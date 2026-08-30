// app/api/assistant/route.ts — AI assistant over the user's projects (RLS-enforced).
import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import OpenAI from "openai";

const openai = new OpenAI();

export async function POST(req: NextRequest) {
  const session = await getServerSession();
  const { message } = await req.json();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  // Anon-key client that carries the user's auth context. Row-Level Security
  // policies on `projects` restrict every row to its owner at the database
  // level — the credential cannot read other users' rows even if asked to.
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: () => cookies() }
  );

  const { data: projects } = await supabase
    .from("projects")
    .select("id, name, status, budget");

  const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    response_format: { type: "json_object" },
    messages: [
      { role: "system", content: 'You are a project assistant. Reply as JSON {"reply": "..."}.' },
      { role: "system", content: `Projects: ${JSON.stringify(projects)}` },
      { role: "user", content: message },
    ],
  });

  let reply = "";
  try {
    reply = JSON.parse(completion.choices[0].message.content ?? "{}").reply ?? "";
  } catch {
    reply = "";
  }
  return NextResponse.json({ reply: String(reply) });
}
