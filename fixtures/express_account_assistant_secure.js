// AI account assistant: scoped version. Mounted at /api/assistant.
const express = require("express");
const crypto = require("crypto");
const { Pool } = require("pg");
const OpenAI = require("openai");
const { requireAuth } = require("./middleware"); // sets req.user from verified session
const logger = require("./logger");

const router = express.Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const openai = new OpenAI();

const SYSTEM_PROMPT =
  'You are an account assistant. Answer the user\'s question. Reply as JSON: {"answer": "..."}.';

router.post("/", requireAuth, async (req, res) => {
  const { message } = req.body;
  logger.info("assistant.request", { userId: req.user.id });

  // Identity comes from the verified session, and the query is scoped to it.
  const { rows } = await pool.query(
    "SELECT subscription, invoices FROM users WHERE id = $1",
    [req.user.id]
  );

  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-4o",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "system", content: `Account: ${JSON.stringify(rows[0])}` },
        { role: "user", content: message },
      ],
    });

    const parsed = JSON.parse(completion.choices[0].message.content);
    // Return only the whitelisted field.
    return res.json({ answer: String(parsed.answer ?? "") });
  } catch (err) {
    // Log details server-side; hand the client a generic message + trace id.
    const traceId = crypto.randomUUID();
    logger.error("assistant.failed", { traceId, err: err.message });
    return res.status(500).json({ error: "Request failed", traceId });
  }
});

module.exports = router;
