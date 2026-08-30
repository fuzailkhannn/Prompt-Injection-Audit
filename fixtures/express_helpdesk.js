// Helpdesk routes. Users file tickets; staff get an AI-generated daily digest.
const express = require("express");
const { Pool } = require("pg");
const OpenAI = require("openai");
const { requireAuth, requireStaff } = require("./middleware");

const router = express.Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const openai = new OpenAI();

// A logged-in user files a support ticket. The body is free text.
router.post("/tickets", requireAuth, async (req, res) => {
  const { subject, body } = req.body;
  await pool.query(
    "INSERT INTO tickets (user_id, subject, body, created_at) VALUES ($1, $2, $3, now())",
    [req.user.id, subject, body]
  );
  res.json({ ok: true });
});

// Staff-only: summarize today's tickets into a digest for the support team.
router.get("/tickets/digest", requireAuth, requireStaff, async (req, res) => {
  const { rows } = await pool.query(
    "SELECT subject, body FROM tickets WHERE created_at::date = now()::date"
  );
  const ticketText = rows
    .map((t, i) => `Ticket ${i + 1}: ${t.subject}\n${t.body}`)
    .join("\n\n");

  const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: "Summarize these support tickets for the staff dashboard. Highlight urgent issues and suggested actions." },
      { role: "user", content: ticketText },
    ],
  });

  res.json({ digest: completion.choices[0].message.content });
});

module.exports = router;
