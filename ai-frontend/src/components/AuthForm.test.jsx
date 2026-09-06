import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AuthForm from "./AuthForm";
import * as authApi from "../lib/authApi";

vi.mock("../lib/authApi");

describe("AuthForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("يعرض نموذج الدخول افتراضيًا", () => {
    render(<AuthForm onAuthenticated={vi.fn()} />);
    expect(screen.getByPlaceholderText("البريد الإلكتروني")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "دخول" })).toBeInTheDocument();
  });

  it("يتحول لنموذج إنشاء حساب عند الضغط على زر التبديل", async () => {
    const user = userEvent.setup();
    render(<AuthForm onAuthenticated={vi.fn()} />);
    await user.click(screen.getByText("ليس لديك حساب؟ أنشئ واحدًا"));
    expect(screen.getByRole("button", { name: "إنشاء حساب" })).toBeInTheDocument();
  });

  it("عند نجاح الدخول ينادي onAuthenticated دون تخزين التوكن في localStorage", async () => {
    authApi.loginUser.mockResolvedValue({
      access_token: "fake-access",
      refresh_token: "fake-refresh",
    });
    const onAuthenticated = vi.fn();
    const user = userEvent.setup();

    render(<AuthForm onAuthenticated={onAuthenticated} />);
    await user.type(screen.getByPlaceholderText("البريد الإلكتروني"), "test@example.com");
    await user.type(screen.getByPlaceholderText(/كلمة المرور/), "StrongPass123");
    await user.click(screen.getByRole("button", { name: "دخول" }));

    await waitFor(() => expect(onAuthenticated).toHaveBeenCalled());
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(authApi.registerUser).not.toHaveBeenCalled();
  });

  it("عند فشل الدخول يعرض رسالة الخطأ القادمة من الخادم", async () => {
    authApi.loginUser.mockRejectedValue({
      response: { data: { detail: "بريد إلكتروني أو كلمة مرور غير صحيحة" } },
    });
    const user = userEvent.setup();

    render(<AuthForm onAuthenticated={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("البريد الإلكتروني"), "test@example.com");
    await user.type(screen.getByPlaceholderText(/كلمة المرور/), "WrongPass123");
    await user.click(screen.getByRole("button", { name: "دخول" }));

    expect(await screen.findByText("بريد إلكتروني أو كلمة مرور غير صحيحة")).toBeInTheDocument();
  });

  it("عند إنشاء حساب جديد ينادي registerUser ثم loginUser بنفس البيانات", async () => {
    authApi.registerUser.mockResolvedValue({ id: 1, email: "new@example.com" });
    authApi.loginUser.mockResolvedValue({
      access_token: "fake-access",
      refresh_token: "fake-refresh",
    });
    const onAuthenticated = vi.fn();
    const user = userEvent.setup();

    render(<AuthForm onAuthenticated={onAuthenticated} />);
    await user.click(screen.getByText("ليس لديك حساب؟ أنشئ واحدًا"));
    await user.type(screen.getByPlaceholderText("البريد الإلكتروني"), "new@example.com");
    await user.type(screen.getByPlaceholderText(/كلمة المرور/), "StrongPass123");
    await user.click(screen.getByRole("button", { name: "إنشاء حساب" }));

    await waitFor(() =>
      expect(authApi.registerUser).toHaveBeenCalledWith("new@example.com", "StrongPass123")
    );
    expect(authApi.loginUser).toHaveBeenCalledWith("new@example.com", "StrongPass123");
    expect(onAuthenticated).toHaveBeenCalled();
  });
});
