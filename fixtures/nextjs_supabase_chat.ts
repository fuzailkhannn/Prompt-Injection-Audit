// app/api/assistant/route.ts: AI assistant over the user's projects.
import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { createClient } from "@supabase/supabase-js";
import OpenAI from "openai";

// Server-side Supabase client used for all assistant queries.
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const openai = new OpenAI();

export async function POST(req: NextRequest) {
  const session = await getServerSession();
  const { message } = await req.json();

  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  // Only fetch this user's projects.
  const { data: projects } = await supabase
    .from("projects")
    .select("id, name, status, budget, notes")
    .eq("owner_id", session.user.id);

  const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: "You are a project assistant. Answer using the user's project data." },
      { role: "system", content: `Projects: ${JSON.stringify(projects)}` },
      { role: "user", content: message },
    ],
  });

  const parsed = completion.choices[0].message.content ?? "";
  return NextResponse.json({ reply: parsed });
}
