// app/api/chat/route.ts: chat endpoint for the dashboard assistant.
import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { sql } from "@/lib/db";
import OpenAI from "openai";

const openai = new OpenAI();

const SYSTEM = `You are the dashboard assistant. Help the user understand their metrics.`;

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession();
    const { message } = await req.json();

    // Load this user's metrics for context.
    const metrics = await sql`
      SELECT metric, value, day FROM metrics
      WHERE account_id = ${session?.user?.id ?? ""}
    `;

    const completion = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        { role: "system", content: SYSTEM },
        { role: "system", content: `Metrics: ${JSON.stringify(metrics)}` },
        { role: "user", content: message },
      ],
    });

    // Send the model's answer straight back to the browser.
    return new NextResponse(completion.choices[0].message.content, {
      headers: { "Content-Type": "text/plain" },
    });
  } catch (err: any) {
    // Surface the error so the frontend can display what went wrong.
    return NextResponse.json(
      { error: err.message, stack: err.stack },
      { status: 500 }
    );
  }
}
