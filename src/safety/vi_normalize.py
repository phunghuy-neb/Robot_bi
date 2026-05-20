"""
vi_normalize.py — Chuẩn hoá văn bản tiếng Việt để fuzzy match
==============================================================
Dùng nội bộ trong src/safety/ để xử lý cả hai trường hợp:
  - Bé gõ có dấu: "muốn chết" → normalize → "muon chet"
  - Bé gõ không dấu: "muon chet" → normalize → "muon chet"

Không phụ thuộc thư viện ngoài — chỉ dùng stdlib `unicodedata`.
"""

import unicodedata

# Ký tự đặc biệt tiếng Việt không decompose qua NFD cần xử lý thủ công
_VI_SPECIAL = str.maketrans({
    'đ': 'd', 'Đ': 'D',
    'ơ': 'o', 'Ơ': 'O',
    'ư': 'u', 'Ư': 'U',
    'ă': 'a', 'Ă': 'A',
})


def normalize_vi(text: str) -> str:
    """
    Chuẩn hoá văn bản tiếng Việt: bỏ dấu → ASCII lowercase.

    Ví dụ:
      "Muốn chết" → "muon chet"
      "Bị đánh"   → "bi danh"
      "muon chet"  → "muon chet"  (giữ nguyên nếu đã không dấu)

    Args:
        text: Văn bản gốc (có thể có hoặc không có dấu tiếng Việt).

    Returns:
        Chuỗi ASCII lowercase, đã bỏ dấu.
    """
    # Bước 1: Xử lý ký tự đặc biệt (đ, ơ, ư, ă) không có canonical decomposition
    text = text.translate(_VI_SPECIAL)
    # Bước 2: NFD decomposition → tách tổ hợp dấu khỏi ký tự cơ sở
    nfd = unicodedata.normalize('NFD', text)
    # Bước 3: Encode ASCII (bỏ combining chars) → lowercase
    return nfd.encode('ascii', 'ignore').decode('ascii').lower()


if __name__ == "__main__":
    cases = [
        ("Muốn chết", "muon chet"),
        ("Bị đánh", "bi danh"),
        ("Không ai chơi với con", "khong ai choi voi con"),
        ("muon chet", "muon chet"),
        ("Số mẹ là 0912345678", "so me la 0912345678"),
    ]
    all_pass = True
    for text, expected in cases:
        result = normalize_vi(text)
        ok = result == expected
        if not ok:
            all_pass = False
        print(f"  {'PASS' if ok else 'FAIL'}  '{text}' → '{result}' (expect '{expected}')")
    print("ALL PASS ✅" if all_pass else "SOME FAILED ❌")
