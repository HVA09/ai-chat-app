import api from "./api";

export async function getPlans() {
  const { data } = await api.get("/billing/plans");
  return data;
}

export async function getMySubscription() {
  const { data } = await api.get("/billing/subscription");
  return data;
}

export async function createCheckout(planId) {
  const { data } = await api.post("/billing/checkout", {
    plan_id: planId,
    success_url: `${window.location.origin}/billing/success`,
    cancel_url: `${window.location.origin}/billing/cancel`,
  });
  return data;
}

export async function cancelSubscription() {
  const { data } = await api.post("/billing/cancel");
  return data;
}
