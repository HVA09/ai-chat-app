import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export default function useDirection() {
  const { i18n } = useTranslation();

  useEffect(() => {
    const rtl = i18n.language === "ar";
    document.documentElement.dir = rtl ? "rtl" : "ltr";
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);
}
