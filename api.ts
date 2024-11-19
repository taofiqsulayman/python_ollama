import axios from "axios";
import {
    AnalysisInstruction,
    ChatMessage,
    Project,
    User,
    AnalysisResponse,
    FileResponse,
} from "../types";

export interface AnalysisInstruction {
    title: string;
    description: string;
    data_type: string;
}

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    timestamp?: string;
}

export interface Project {
    id: number;
    name: string;
    description?: string;
    created_at: string;
}

export interface User {
    id: string;
    username: string;
    role: string;
}

export interface AnalysisResponse {
    id: number;
    instructions: AnalysisInstruction[];
    results: Record<string, any>;
    created_at: string;
}

export interface FileResponse {
    id: number;
    file_name: string;
    content: string;
    created_at: string;
}

const api = axios.create({
    baseURL: "http://localhost:8000/api/v1",
});

export const fileProcessorApi = {
    getCurrentUser: () => api.get<User>("/users/me"),

    createProject: (data: { name: string; description?: string }) =>
        api.post<Project>("/projects", data),

    getProjects: () => api.get<Project[]>("/projects"),

    uploadFiles: (projectId: number, files: FileList) => {
        const formData = new FormData();
        Array.from(files).forEach((file) => {
            formData.append("files", file);
        });
        return api.post(`/projects/${projectId}/files`, formData);
    },

    getFiles: (projectId: number) =>
        api.get<FileResponse[]>(`/projects/${projectId}/files`),

    runAnalysis: (projectId: number, instructions: AnalysisInstruction[]) =>
        api.post<AnalysisResponse>(`/projects/${projectId}/analyze`, { instructions }),

    sendMessage: (
        projectId: number,
        data: {
            prompt: string;
            chat_type: "document" | "image";
            image_data?: string;
        }
    ) =>
        api.post<ChatMessage>(
            `/projects/${projectId}/chat`,
            data
        ),

    getChatHistory: (projectId: number, chatType?: "document" | "image") =>
        api.get<{ history: ChatMessage[] }>(`/projects/${projectId}/chat-history`, {
            params: { chat_type: chatType },
        }),
};
