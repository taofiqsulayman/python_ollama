# Local Development Setup Guide

## Prerequisites

1. Python 3.8+ installed
2. Docker installed
3. pip or poetry for Python package management

## Step 1: Environment Setup

1. Create a new virtual environment:
```bash
# Using venv
python -m venv venv

# Activate the virtual environment
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Step 2: PostgreSQL Setup with Docker

1. Create a Docker container for PostgreSQL:
```bash
docker run --name fileprocessor-db \
  -e POSTGRES_DB=fileprocessor \
  -e POSTGRES_USER=fileprocessor \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  -d postgres:14
```

2. Verify the container is running:
```bash
docker ps
```

## Step 3: Environment Variables

Create a `.env` file in your project root:
```env
# Database
DATABASE_URL=postgresql://fileprocessor:yourpassword@localhost:5432/fileprocessor

```
## step 4: use local setup

edit models.py to use the local database instance

## step 5: run the app

streamlit run app.py

fastapi run main.py


## API Usage Examples

npm install @tanstack/react-query axios


// types.ts
export interface User {
  id: string;
  username: string;
  role: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  created_at: string;
}

export interface ChatSession {
  id: number;
  name?: string;
  files: number[];
  session_type: 'document' | 'image';
  created_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  additional_data?: Record<string, any>;
}

export interface AnalysisInstruction {
  title: string;
  data_type: 'string' | 'number';
  description: string;
}

// api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
});

export const fileProcessorApi = {
  getCurrentUser: () => 
    api.get<User>('/users/me'),

  createProject: (data: { name: string; description?: string }) =>
    api.post<Project>('/projects', data),
  
  getProjects: () =>
    api.get<Project[]>('/projects'),

  uploadFiles: (projectId: number, files: FileList) => {
    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });
    return api.post(`/projects/${projectId}/files`, formData);
  },

  createChatSession: (projectId: number, data: {
    name?: string;
    file_ids: number[];
    session_type: 'document' | 'image';
  }) =>
    api.post<ChatSession>(`/projects/${projectId}/chat-sessions`, data),

  getChatSessions: (projectId: number, type?: 'document' | 'image') =>
    api.get<ChatSession[]>(`/projects/${projectId}/chat-sessions`, {
      params: { session_type: type }
    }),

  sendMessage: (sessionId: number, data: {
    content: string;
    additional_data?: Record<string, any>;
  }) =>
    api.post<{ response: string }>(`/chat-sessions/${sessionId}/messages`, data),

  getChatMessages: (sessionId: number) =>
    api.get<{ messages: ChatMessage[] }>(`/chat-sessions/${sessionId}/messages`),

  runAnalysis: (projectId: number, instructions: AnalysisInstruction[]) =>
    api.post(`/projects/${projectId}/analyze`, { instructions }),
};


// hooks/useFileProcessor.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { fileProcessorApi } from '../api';

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => fileProcessorApi.getCurrentUser().then(res => res.data),
  });
};

export const useProjects = () => {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => fileProcessorApi.getProjects().then(res => res.data),
  });
};

export const useCreateProject = () => {
  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      fileProcessorApi.createProject(data).then(res => res.data),
  });
};

export const useUploadFiles = (projectId: number) => {
  return useMutation({
    mutationFn: (files: FileList) =>
      fileProcessorApi.uploadFiles(projectId, files),
  });
};

export const useChatSessions = (projectId: number, type?: 'document' | 'image') => {
  return useQuery({
    queryKey: ['chatSessions', projectId, type],
    queryFn: () => fileProcessorApi.getChatSessions(projectId, type).then(res => res.data),
  });
};

export const useCreateChatSession = () => {
  return useMutation({
    mutationFn: (data: {
      projectId: number;
      name?: string;
      file_ids: number[];
      session_type: 'document' | 'image';
    }) =>
      fileProcessorApi.createChatSession(data.projectId, {
        name: data.name,
        file_ids: data.file_ids,
        session_type: data.session_type,
      }).then(res => res.data),
  });
};

export const useChatMessages = (sessionId: number) => {
  return useQuery({
    queryKey: ['chatMessages', sessionId],
    queryFn: () => fileProcessorApi.getChatMessages(sessionId).then(res => res.data.messages),
  });
};

export const useSendMessage = (sessionId: number) => {
  return useMutation({
    mutationFn: (data: { content: string; additional_data?: Record<string, any> }) =>
      fileProcessorApi.sendMessage(sessionId, data).then(res => res.data),
  });
};


// Example components showing how to use the hooks

// ProjectList.tsx
const ProjectList = () => {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      {projects?.map(project => (
        <div key={project.id}>{project.name}</div>
      ))}
    </div>
  );
};

// ChatComponent.tsx
const ChatComponent = ({ sessionId }: { sessionId: number }) => {
  const { data: messages, isLoading } = useChatMessages(sessionId);
  const sendMessage = useSendMessage(sessionId);

  const handleSendMessage = async (content: string) => {
    await sendMessage.mutateAsync({ content });
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      {messages?.map(message => (
        <div key={message.timestamp}>
          {message.role}: {message.content}
        </div>
      ))}
    </div>
  );
};

### cURL Examples

curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "description": "Test Description"}'

curl -X GET http://localhost:8000/api/v1/projects

curl -X POST http://localhost:8000/api/v1/projects/1/files \
  -F "files=@/path/to/file.pdf" \
  -F "files=@/path/to/another.docx"

curl -X GET http://localhost:8000/api/v1/projects/1/files

curl -X POST http://localhost:8000/api/v1/projects/1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": [
      {
        "title": "Extract Date",
        "data_type": "string",
        "description": "Find the document date"
      }
    ]
  }'

curl -X POST http://localhost:8000/api/v1/projects/1/chat-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Chat",
    "file_ids": [1, 2],
    "session_type": "document"
  }'

curl -X GET http://localhost:8000/api/v1/projects/1/chat-sessions

curl -X POST http://localhost:8000/api/v1/chat-sessions/1/update \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Chat Name"}'

curl -X POST http://localhost:8000/api/v1/chat-sessions/1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What does the document say about X?",
    "additional_data": null
  }'

curl -X GET http://localhost:8000/api/v1/chat-sessions/1/messages
```