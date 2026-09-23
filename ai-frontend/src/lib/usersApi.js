import api from "./api";

export async function getCurrentUser() {
  const { data } = await api.get("/users/me");
  return data;
}

export async function updateProfile(fields) {
  const { data } = await api.patch("/users/me", fields);
  return data;
}

export async function changePassword(currentPassword, newPassword) {
  const { data } = await api.post("/users/me/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
}

export async function deleteAccount(password) {
  await api.request({ method: "DELETE", url: "/users/me", data: { password } });
}

export async function exportAccountData() {
  const response = await api.get("/users/me/export", { responseType: "blob" });
  const disposition = response.headers["content-disposition"] || "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] || "ai-chat-account-export.json";
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
