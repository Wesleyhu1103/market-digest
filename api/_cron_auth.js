// Shared auth helper for the Vercel cron backup. The endpoint can dispatch a
// GitHub workflow with a PAT, so missing configuration must fail closed.
export function authorizeCron(req) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false;
  const auth = req.headers.authorization || "";
  return auth === `Bearer ${secret}`;
}
