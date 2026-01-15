import { NextRequest, NextResponse } from "next/server";

const XAI_API_URL = "https://api.x.ai/v1/images/generations";

export interface ImageGenerationRequest {
  prompt: string;
  size?: "1024x1024" | "1024x768" | "768x1024";
  n?: number;
}

export interface ImageGenerationResponse {
  success: boolean;
  images?: Array<{
    url: string;
    revised_prompt?: string;
  }>;
  error?: string;
}

export async function POST(request: NextRequest): Promise<NextResponse<ImageGenerationResponse>> {
  try {
    const apiKey = process.env.XAI_API_KEY || process.env.NEXT_PUBLIC_XAI_API_KEY;

    if (!apiKey) {
      return NextResponse.json(
        { success: false, error: "XAI API key not configured" },
        { status: 500 }
      );
    }

    const body: ImageGenerationRequest = await request.json();

    if (!body.prompt || typeof body.prompt !== "string") {
      return NextResponse.json(
        { success: false, error: "Prompt is required" },
        { status: 400 }
      );
    }

    // Enhance prompt for better educational/conceptual illustrations
    const enhancedPrompt = `Educational illustration: ${body.prompt}. Style: clean, modern, professional diagram or illustration suitable for learning. Clear labels if applicable. White or light background.`;

    const response = await fetch(XAI_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "grok-2-image",
        prompt: enhancedPrompt,
        n: body.n || 1,
        size: body.size || "1024x1024",
        response_format: "url",
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Grok image generation error:", errorText);

      // Check if it's a model not available error and try alternative
      if (response.status === 404 || errorText.includes("model")) {
        // Try with aurora model name
        const altResponse = await fetch(XAI_API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model: "aurora",
            prompt: enhancedPrompt,
            n: body.n || 1,
            size: body.size || "1024x1024",
            response_format: "url",
          }),
        });

        if (altResponse.ok) {
          const altData = await altResponse.json();
          return NextResponse.json({
            success: true,
            images: altData.data.map((img: { url: string; revised_prompt?: string }) => ({
              url: img.url,
              revised_prompt: img.revised_prompt,
            })),
          });
        }
      }

      return NextResponse.json(
        { success: false, error: `Image generation failed: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: true,
      images: data.data.map((img: { url: string; revised_prompt?: string }) => ({
        url: img.url,
        revised_prompt: img.revised_prompt,
      })),
    });
  } catch (error) {
    console.error("Image generation error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
