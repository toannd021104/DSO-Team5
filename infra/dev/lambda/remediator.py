"""Namespace-scoped reversible NetworkPolicy quarantine for approved lab pods."""

import base64
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import boto3
from botocore.auth import SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

log = logging.getLogger()
log.setLevel(logging.INFO)

REGION = os.environ["AWS_REGION"]
CLUSTER = os.environ["CLUSTER"]
NAMESPACE = os.environ["NAMESPACE"]
PREFIX = os.environ["POLICY_PREFIX"]
eks = boto3.client("eks", region_name=REGION)
table = boto3.resource("dynamodb", region_name=REGION).Table(os.environ["TABLE_NAME"])


def _token():
    credentials = boto3.Session().get_credentials().get_frozen_credentials()
    signed = AWSRequest(
        method="GET",
        url=f"https://sts.{REGION}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
        headers={"x-k8s-aws-id": CLUSTER},
    )
    SigV4QueryAuth(Credentials(credentials.access_key, credentials.secret_key, credentials.token), "sts", REGION, expires=60).add_auth(signed)
    return "k8s-aws-v1." + base64.urlsafe_b64encode(signed.url.encode()).decode().rstrip("=")


def _request(path, method="GET", body=None):
    cluster = eks.describe_cluster(name=CLUSTER)["cluster"]
    endpoint = cluster["endpoint"].rstrip("/")
    ca = base64.b64decode(cluster["certificateAuthority"]["data"])
    request_body = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        endpoint + path,
        data=request_body,
        method=method,
        headers={"Authorization": f"Bearer {_token()}", "Accept": "application/json", "Content-Type": "application/json"},
    )
    import ssl
    context = ssl.create_default_context(cadata=ca.decode())
    try:
        with urllib.request.urlopen(request, context=context, timeout=12) as response:
            return json.loads(response.read()) if response.status != 204 else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode(errors="replace")
        raise RuntimeError(f"Kubernetes API {method} {path} returned {exc.code}: {payload[:300]}") from exc


def _update_status(finding_id, status, extra=None):
    values = {":s": status}
    expression = "SET #s=:s"
    names = {"#s": "status"}
    if extra:
        expression += ", #resp=:r"
        names["#resp"] = "response"
        values[":r"] = json.dumps(extra)
    table.update_item(Key={"finding_id": finding_id}, UpdateExpression=expression, ExpressionAttributeNames=names, ExpressionAttributeValues=values)


def _policy_name(finding_id):
    if not re.fullmatch(r"[A-Fa-f0-9]{8,64}", finding_id or ""):
        raise ValueError("Finding ID is not a valid GuardDuty ID")
    return PREFIX + finding_id.lower()[:48]


def _release(finding_id):
    name = _policy_name(finding_id)
    path = f"/apis/networking.k8s.io/v1/namespaces/{NAMESPACE}/networkpolicies/{name}"
    policy = _request(path)
    labels = (policy.get("metadata") or {}).get("labels") or {}
    if labels.get("guarduty.io/finding-id") != finding_id:
        raise RuntimeError("Refusing to delete a policy without the matching incident label")
    _request(path, method="DELETE", body={"apiVersion": "v1", "kind": "DeleteOptions"})
    _update_status(finding_id, "RELEASED", {"policy": name, "reason": "15-minute containment window expired"})
    return {"finding_id": finding_id, "status": "RELEASED", "policy": name}


def handler(event, _context):
    finding_id = event.get("finding_id")
    if event.get("action") == "release":
        return _release(finding_id)

    stored = table.get_item(Key={"finding_id": finding_id}, ConsistentRead=True).get("Item")
    if not stored or stored.get("status") != "CONTAINMENT_CANDIDATE":
        raise ValueError("Only an analyzer-approved incident record may reach containment")
    try:
        analysis = json.loads(stored["analysis"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Stored incident analysis is missing or invalid") from exc
    if (analysis.get("policy") or {}).get("decision") != "QUARANTINE_CANDIDATE":
        raise ValueError("Stored deterministic policy decision does not authorize containment")
    expected = {
        "finding_type": analysis.get("finding_type"),
        "severity": analysis.get("severity"),
        "cluster": (analysis.get("target") or {}).get("cluster"),
        "namespace": (analysis.get("target") or {}).get("namespace"),
        "workload": (analysis.get("target") or {}).get("workload"),
    }
    for key, expected_value in expected.items():
        if event.get(key) != expected_value:
            raise ValueError(f"Containment request {key} does not match the stored analysis")

    if event.get("cluster") != CLUSTER or event.get("namespace") != NAMESPACE:
        raise ValueError("Policy gate target does not match the configured lab cluster and namespace")
    if event.get("finding_type") != "AttackSequence:EKS/CompromisedCluster" or event.get("severity", 0) < 9:
        raise ValueError("Only critical EKS attack-sequence findings may reach the response adapter")

    pod_name = event.get("workload")
    if not pod_name or "*" in pod_name:
        raise ValueError("A single exact pod name is required")
    pod_path = f"/api/v1/namespaces/{NAMESPACE}/pods/{urllib.parse.quote(pod_name, safe='')}"
    pod = _request(pod_path)
    metadata = pod.get("metadata") or {}
    labels = metadata.get("labels") or {}
    if metadata.get("deletionTimestamp"):
        raise ValueError("Target pod is terminating")
    if labels.get("guarduty.io/auto-quarantine") != "true":
        raise ValueError("Target pod has not opted into automatic quarantine")
    if (pod.get("spec") or {}).get("hostNetwork"):
        raise ValueError("hostNetwork pods are outside the NetworkPolicy containment scope")
    if not metadata.get("ownerReferences"):
        raise ValueError("Unmanaged pods are excluded so the response preserves controller ownership")
    if not finding_id:
        raise ValueError("Finding ID is required")

    name = _policy_name(finding_id)
    path = f"/apis/networking.k8s.io/v1/namespaces/{NAMESPACE}/networkpolicies"
    selector_labels = {k: v for k, v in labels.items() if isinstance(k, str) and isinstance(v, str)}
    policy = {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": name,
            "namespace": NAMESPACE,
            "labels": {"guarduty.io/finding-id": finding_id, "app.kubernetes.io/managed-by": "guarduty-response"},
            "annotations": {"guarduty.io/pod": pod_name, "guarduty.io/expires-after-seconds": "900"},
        },
        "spec": {"podSelector": {"matchLabels": selector_labels}, "policyTypes": ["Ingress", "Egress"]},
    }
    try:
        _request(path, method="POST", body=policy)
    except RuntimeError as exc:
        if "returned 409" not in str(exc):
            raise
        existing = _request(path + "/" + name)
        existing_labels = (existing.get("metadata") or {}).get("labels") or {}
        if existing_labels.get("guarduty.io/finding-id") != finding_id:
            raise RuntimeError("An unrelated NetworkPolicy already uses the action name") from exc

    try:
        verified = _request(path + "/" + name)
        verified_selector = ((verified.get("spec") or {}).get("podSelector") or {}).get("matchLabels") or {}
        if verified_selector != selector_labels:
            raise RuntimeError("NetworkPolicy verification failed: selector differs from the observed pod labels")
        _update_status(finding_id, "QUARANTINED", {"policy": name, "namespace": NAMESPACE, "pod": pod_name, "expires_after_seconds": 900, "verification": "NetworkPolicy object persisted; data-plane verification is tracked separately"})
    except Exception:
        try:
            _request(f"{path}/{name}", method="DELETE", body={"apiVersion": "v1", "kind": "DeleteOptions"})
        except Exception:
            log.exception("Containment compensation failed for policy %s", name)
        raise
    log.warning("Applied policy %s to opted-in pod %s/%s", name, NAMESPACE, pod_name)
    return {"finding_id": finding_id, "status": "QUARANTINED", "policy": name, "pod": pod_name, "namespace": NAMESPACE, "expires_after_seconds": 900}
