"""
قواعد تحقق مشتركة (كلمات المرور، البريد) — مصدر واحد بدل تكرار في schemas
"""
import re

_PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$")

PASSWORD_HINT_AR = (
    "كلمة المرور يجب أن تكون 8–128 حرفًا وتحتوي حرفًا كبيرًا وصغيرًا ورقمًا على الأقل"
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_strong_password(password: str) -> str:
    if not _PASSWORD_PATTERN.match(password):
        raise ValueError(PASSWORD_HINT_AR)
    return password
