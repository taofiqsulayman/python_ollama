import axios from "axios";
import {
    AnalysisInstruction,
    ChatMessage,
    Project,
    User,
    AnalysisResponse,
    FileResponse,
} from "../types";

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
