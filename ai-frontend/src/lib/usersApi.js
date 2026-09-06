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
