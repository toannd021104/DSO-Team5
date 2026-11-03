"""Evidence-first, deterministic GuardDuty finding analysis."""

import datetime as dt
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger()
log.setLevel(logging.INFO)

REGION = os.environ["AWS_REGION"]
ACCOUNT = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
DETECTOR_ID = os.environ["DETECTOR_ID"]
guardduty = boto3.client("guardduty", region_name=REGION)
cloudtrail = boto3.client("cloudtrail", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION).Table(os.environ["TABLE_NAME"])
s3 = boto3.client("s3", region_name=REGION)


def _resources(finding):
    sequence = (((finding.get("Service") or {}).get("Detection") or {}).get("Sequence") or {})
    return sequence.get("Resources") or finding.get("Resources") or []


def _evidence(finding):
    resources = _resources(finding)
    clusters, workloads, containers = [], [], []
    for resource in resources:
        kind = resource.get("ResourceType")
        data = resource.get("Data") or {}
        if kind == "EKS_CLUSTER":
            cluster = data.get("EksCluster") or {}
            clusters.append({"name": resource.get("Name"), "arn": resource.get("Uid"), "account": resource.get("AccountId"), "status": cluster.get("Status")})
        elif kind == "KUBERNETES_WORKLOAD":
            workload = data.get("KubernetesWorkload") or {}
            workloads.append({"name": resource.get("Name"), "namespace": workload.get("Namespace"), "kind": workload.get("KubernetesResourcesTypes"), "container_uids": workload.get("ContainerUids", [])})
        elif kind == "CONTAINER":
            container = data.get("Container") or {}
            containers.append({"name": resource.get("Name"), "uid": resource.get("Uid"), "image": container.get("Image"), "image_uid": container.get("ImageUid")})
    sequence = (((finding.get("Service") or {}).get("Detection") or {}).get("Sequence") or {})
    actors = sequence.get("Actors") or []
    signals = sequence.get("Signals") or []
    indicators = sequence.get("SequenceIndicators") or []
    service = finding.get("Service") or {}
    resource = finding.get("Resource") or {}
    instance = resource.get("InstanceDetails") or {}
    eks = resource.get("EksClusterDetails") or instance.get("EksClusterDetails") or {}
    if eks.get("Name"):
        clusters.append({"name": eks.get("Name"), "arn": eks.get("Arn"), "account": finding.get("AccountId"), "status": eks.get("Status")})
    kubernetes = ((resource.get("KubernetesDetails") or {}).get("KubernetesWorkloadDetails") or {})
    if kubernetes.get("Name"):
        workloads.append({
            "name": kubernetes.get("Name"),
            "namespace": kubernetes.get("Namespace"),
            "kind": kubernetes.get("Type"),
            "container_uids": [c.get("Id") for c in kubernetes.get("Containers", []) if c.get("Id")],
        })
    for container in kubernetes.get("Containers", []):
        containers.append({"name": container.get("Name"), "uid": container.get("Id"), "image": container.get("Image")})
    runtime = service.get("RuntimeDetails") or {}
    process = runtime.get("Process") or {}
    dns = ((service.get("Action") or {}).get("DnsRequestAction") or {})
    runtime_context = {
        "instance": {"id": instance.get("InstanceId"), "type": instance.get("InstanceType")} if instance else {},
        "process": process,
        "dns_request": dns,
    } if process or dns or instance else {}
    if not signals and (finding.get("Type") or finding.get("Description")):
        signals = [{
            "Name": finding.get("Type"),
            "Description": finding.get("Description"),
            "FirstSeenAt": service.get("EventFirstSeen"),
            "LastSeenAt": service.get("EventLastSeen"),
        }]
    return {
        "clusters": clusters,
        "workloads": workloads,
        "containers": containers,
        "actors": [{"id": a.get("Id"), "user": (a.get("User") or {}).get("Name"), "type": (a.get("User") or {}).get("Type")} for a in actors],
        "signals": [{"type": s.get("Name"), "description": s.get("Description"), "first_seen": s.get("FirstSeenAt"), "last_seen": s.get("LastSeenAt")} for s in signals],
        "mitre_indicators": [{"key": i.get("Key"), "values": i.get("Values", [])} for i in indicators],
        "runtime_context": runtime_context,
    }


def _cloudtrail_context(finding):
    sequence = (((finding.get("Service") or {}).get("Detection") or {}).get("Sequence") or {})
    actor = next((a.get("User", {}).get("Name") for a in sequence.get("Actors", []) if a.get("User", {}).get("Name", "").startswith("arn:aws:")), None)
    if not actor:
        return {"status": "no_iam_actor_in_finding", "events": []}
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=1)
    try:
        result = cloudtrail.lookup_events(
            LookupAttributes=[{"AttributeKey": "Username", "AttributeValue": actor.split("/")[-1]}],
            StartTime=start,
            EndTime=end,
            MaxResults=20,
        )
        events = []
        for event in result.get("Events", []):
            events.append({"event_name": event.get("EventName"), "event_time": event.get("EventTime"), "username": event.get("Username"), "event_id": event.get("EventId")})
        return {"status": "queried", "events": events}
    except ClientError as exc:
        log.warning("CloudTrail enrichment unavailable: %s", exc.response.get("Error", {}).get("Code"))
        return {"status": "unavailable", "events": []}


def handler(event, _context):
    if event.get("source") != "aws.guardduty" or event.get("detail-type") != "GuardDuty Finding":
        raise ValueError("Unexpected EventBridge source or detail type")
    if event.get("account") != ACCOUNT or event.get("region") != REGION:
        raise ValueError("Finding event account or region does not match this analyzer")
    detail = event.get("detail") or {}
    if ((detail.get("service") or {}).get("detectorId")) != DETECTOR_ID:
        raise ValueError("Finding event detector does not match the configured GuardDuty detector")
    finding_id = detail.get("id") or detail.get("Id")
    if not finding_id:
        raise ValueError("Finding ID is required")

    try:
        response = guardduty.get_findings(DetectorId=detail["service"]["detectorId"], FindingIds=[finding_id])
        if not response.get("Findings"):
            raise ValueError("GuardDuty returned no finding for the event ID")
        finding = response["Findings"][0]
    except KeyError as exc:
        log.exception("GuardDuty event is missing its detector ID")
        raise ValueError("GuardDuty event is missing service.detectorId") from exc
    except ClientError as exc:
        log.error("GuardDuty GetFindings failed: %s", exc.response.get("Error", {}))
        raise

    evidence = _evidence(finding)
    cloudtrail_context = _cloudtrail_context(finding)
    has_exact_cluster = any(c.get("name") == os.environ["CLUSTER"] and (not c.get("account") or c.get("account") == ACCOUNT) for c in evidence["clusters"])
    exact_workloads = [w for w in evidence["workloads"] if w.get("namespace") == os.environ["NAMESPACE"] and w.get("name") and "*" not in w["name"]]
    auto_remediate = (
        os.environ.get("MODE") == "auto"
        and event.get("account") == ACCOUNT
        and event.get("region") == REGION
        and finding.get("Type") == "AttackSequence:EKS/CompromisedCluster"
        and finding.get("Severity", 0) >= 9
        and has_exact_cluster
        and len(exact_workloads) == 1
        and exact_workloads[0].get("kind", "").lower() == "pods"
    )
    rationale = "Exact critical EKS attack sequence and opted-in sandbox target candidate." if auto_remediate else "Evidence did not satisfy every account, region, cluster, namespace, workload, severity, and opt-in gate; notify-only."
    finding_type = finding.get("Type") or "unknown"
    root_cause_hypothesis = (
        "A correlated EKS attack sequence includes the observed signals and actors; root cause remains a hypothesis until verified against workload and audit evidence."
        if finding_type == "AttackSequence:EKS/CompromisedCluster"
        else f"GuardDuty reported {finding_type}; use the recorded runtime process, resource, and network evidence to investigate the initiating behavior. This is a triage hypothesis, not a confirmed root cause."
    )
    root_cause = {
        "hypothesis": root_cause_hypothesis,
        "confidence": "medium" if evidence["signals"] and evidence["clusters"] else "low",
        "evidence_sources": ["GuardDuty finding and resource details", "CloudTrail lookup (best effort)"],
        "evidence_gaps": ["Detective graph unavailable or not queried", "EKS pod labels and controller ownership are checked only immediately before containment"],
    }
    record = {
        "finding_id": finding_id,
        "account_id": event.get("account"),
        "region": event.get("region"),
        "finding_type": finding.get("Type"),
        "severity": finding.get("Severity"),
        "title": finding.get("Title"),
        "created_at": finding.get("CreatedAt"),
        "updated_at": finding.get("UpdatedAt"),
        "description": finding.get("Description"),
        "evidence": evidence,
        "cloudtrail_context": cloudtrail_context,
        "root_cause": root_cause,
        "target": {
            "cluster": os.environ["CLUSTER"],
            "namespace": os.environ["NAMESPACE"],
            "workload": exact_workloads[0].get("name") if len(exact_workloads) == 1 else None,
        },
        "policy": {"decision": "QUARANTINE_CANDIDATE" if auto_remediate else "NOTIFY_ONLY", "reason": rationale, "version": "1"},
        "status": "CONTAINMENT_CANDIDATE" if auto_remediate else "ANALYZED_NOTIFY_ONLY",
    }
    s3.put_object(Bucket=os.environ["BUCKET"], Key=f"findings/{finding_id}.json", Body=json.dumps({"event": event, "finding": finding, "analysis": record}, default=str).encode(), ContentType="application/json", ServerSideEncryption="AES256")
    now = dt.datetime.now(dt.timezone.utc)
    try:
        dynamodb.put_item(
            Item={
                "finding_id": finding_id,
                "status": record["status"],
                "created_at": now.isoformat(),
                "expires_at": int(now.timestamp()) + 90 * 86400,
                "analysis": json.dumps(record, default=str),
            },
            ConditionExpression="attribute_not_exists(finding_id)",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            existing = dynamodb.get_item(Key={"finding_id": finding_id}, ConsistentRead=True).get("Item") or {}
            if existing.get("status") == "ANALYZED_NOTIFY_ONLY":
                dynamodb.update_item(
                    Key={"finding_id": finding_id},
                    UpdateExpression="SET analysis = :analysis, last_analyzed_at = :last_analyzed_at",
                    ExpressionAttributeValues={
                        ":analysis": json.dumps(record, default=str),
                        ":last_analyzed_at": now.isoformat(),
                    },
                )
            return {"finding_id": finding_id, "duplicate": True, "auto_remediate": False}
        raise
    log.info("Incident %s decision=%s evidence_signals=%d", finding_id, record["policy"]["decision"], len(evidence["signals"]))
    return {"finding_id": finding_id, "duplicate": False, "auto_remediate": auto_remediate, "decision": record["policy"]["decision"], "reason": rationale, "finding_type": finding.get("Type"), "severity": finding.get("Severity"), "cluster": os.environ["CLUSTER"], "namespace": os.environ["NAMESPACE"], "workload": exact_workloads[0].get("name") if len(exact_workloads) == 1 else None}
