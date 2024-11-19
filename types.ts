
export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    timestamp?: string;
}

// ...other types...