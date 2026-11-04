# Bộ slide Guarduty AI Ops

## Tệp trong thư mục này

- `guarduty-aiops.pptx` — slide dùng để thuyết trình.
- `build_deck.py` — mã nguồn Python tạo slide; dùng để sửa nội dung và build lại.

Lời dẫn tiếng Việt, thông tin nền và giải thích slide-by-slide nằm trong [`docs/presentation-script.md`](../docs/presentation-script.md). Phần giới thiệu dự án cho người mới đọc ở [`docs/project-guide.md`](../docs/project-guide.md).

## Build lại

Yêu cầu Python 3 và `python-pptx`:

```bash
python3 -m pip install python-pptx
python3 presentation/build_deck.py
```

Script ghi đè `presentation/guarduty-aiops.pptx`. Có thể mở bằng PowerPoint, LibreOffice Impress hoặc import vào Google Slides. Slide sử dụng shape và text native để có thể chỉnh sửa.

## Quy tắc cập nhật

1. Cập nhật kết quả thực tế trong README, architecture/research và roadmap trước khi sửa slide.
2. Không trình bày sample finding như attack sequence thật.
3. Nêu rõ finding canary được chủ động tạo, replay hay tự động route qua EventBridge.
4. Tách hiện trạng, kiểm chứng và roadmap; không ghi Detective/Bedrock là đã chạy nếu SCP vẫn chặn.
5. Build lại PPTX sau khi sửa `build_deck.py` và xem từng slide ở chế độ trình chiếu.
