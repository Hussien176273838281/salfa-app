// Checks Instagram for posts published since the last check and
// sends a push notification to everyone who installed the app.
import { GoogleAuth } from "google-auth-library";

const {
  INSTAGRAM_TOKEN,          // Instagram long-lived access token
  FIREBASE_SERVICE_ACCOUNT, // Firebase service-account JSON (whole file contents)
  SINCE,                    // ISO time of the previous check (set by the workflow)
  SITE_URL = "https://salfa-bdaqiqa.vercel.app",
  TEST_MESSAGE,             // optional: send this text right now (manual test)
} = process.env;

if (!FIREBASE_SERVICE_ACCOUNT) { console.log("Firebase not set up yet — skipping."); process.exit(0); }
const sa = JSON.parse(FIREBASE_SERVICE_ACCOUNT);

async function push(title, body, url) {
  const auth = new GoogleAuth({ credentials: sa, scopes: ["https://www.googleapis.com/auth/firebase.messaging"] });
  const token = await (await auth.getClient()).getAccessToken();
  const res = await fetch(`https://fcm.googleapis.com/v1/projects/${sa.project_id}/messages:send`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token.token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ message: {
      topic: "new_posts",
      notification: { title, body },
      data: { title, body, url },
      android: { priority: "high", notification: { channel_id: "new_posts", color: "#FF7A00" } },
    } }),
  });
  if (!res.ok) throw new Error(`FCM ${res.status}: ${await res.text()}`);
  console.log("Sent:", title, "—", body);
}

if (TEST_MESSAGE) { await push("السالفة بدقيقة", TEST_MESSAGE, SITE_URL); process.exit(0); }
if (!INSTAGRAM_TOKEN) { console.log("Instagram not connected yet — skipping."); process.exit(0); }

const since = SINCE ? new Date(SINCE) : new Date(Date.now() - 35 * 60 * 1000);
const r = await fetch(`https://graph.instagram.com/me/media?fields=id,caption,timestamp,permalink&limit=10&access_token=${INSTAGRAM_TOKEN}`);
if (!r.ok) throw new Error(`Instagram ${r.status}: ${await r.text()}`);
const posts = ((await r.json()).data || [])
  .filter(p => new Date(p.timestamp) > since)
  .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

if (!posts.length) { console.log("No new posts since", since.toISOString()); process.exit(0); }

for (const p of posts) {
  const first = (p.caption || "").split("\n")[0].trim();
  const body = first ? (first.length > 90 ? first.slice(0, 90) + "…" : first) : "نزلت سالفة جديدة، شوفها هسه 👀";
  await push("سالفة جديدة 🔥", body, SITE_URL);
}
