import { GoogleGenAI, Type } from "@google/genai";

// Initialize Gemini Client
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const brainstormConnections = async (content: string, contextNodes: string[]) => {
  try {
    const model = 'gemini-3-flash-preview';
    
    const prompt = `
      You are a detective's assistant helping to fill out a conspiracy board / investigation board.
      The user is focusing on this concept: "${content}".
      
      Here is some other context currently on the board: ${contextNodes.join(', ')}.

      Generate 3 to 5 short, punchy related concepts, clues, or leads that should be added to the board connected to "${content}".
      Keep them brief (under 10 words) like sticky notes.
    `;

    const response = await ai.models.generateContent({
      model,
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            ideas: {
              type: Type.ARRAY,
              items: { type: Type.STRING },
              description: "List of related short concepts"
            }
          }
        }
      }
    });

    const jsonText = response.text;
    if (!jsonText) return [];
    
    const parsed = JSON.parse(jsonText);
    return parsed.ideas || [];

  } catch (error) {
    console.error("Gemini brainstorming failed:", error);
    return [];
  }
};