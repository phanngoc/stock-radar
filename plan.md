# News Summary Chatbot - Technical Specification

## 1. Project Overview

### 1.1 Purpose
Build an AI-powered news aggregation and summary system where users can:
- Subscribe to keywords/topics of interest
- Receive daily AI-generated summaries
- Chat with AI about the summarized content
- Access original news sources

### 1.2 Key Features
- Feedly-like keyword tracking
- On-demand daily summaries (generated when user visits)
- Thread-based chat interface
- Interactive Q&A within threads

---

## 2. System Architecture

### 2.1 Technology Stack

**Frontend:**
- Next.js (with Vite)
- shadcn/ui components
- Zustand (state management)
- TailwindCSS (styling)

**Backend:**
- FastAPI (REST API)
- Uvicorn (ASGI server)
- LlamaIndex (RAG & Q&A)
- PostgreSQL (data persistence)

**Infrastructure:**
- News crawler (existing in TrendNews/) - runs daily at 6 AM

---

## 3. Database Schema

### 3.1 Tables

#### `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    fullname VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `keywords`
```sql
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    keyword VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, keyword)
);
```

#### `threads`
```sql
CREATE TABLE threads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,  -- e.g., "Daily Summary - 2025-11-27"
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);
```

#### `messages`
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES threads(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'system', 'user', 'assistant'
    content TEXT NOT NULL,
    metadata JSONB,  -- store original links, sources, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Backend Implementation

### 4.1 Project Structure
```
AnswerMe/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── keywords.py        # Keyword management
│   │   ├── threads.py         # Thread/chat endpoints
│   │   └── query.py           # Q&A query endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration
│   │   ├── security.py        # JWT, password hashing
│   │   └── database.py        # DB connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llama_service.py   # LlamaIndex integration
│   │   └── summary_service.py # News summarization
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
```

### 4.2 Feature: User Authentication

**Files:** 
- `backend/api/auth.py` - API endpoints
- `backend/core/security.py` - Security utilities
- `backend/models/schemas.py` - Pydantic models

**Endpoints:**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

**Pydantic Schemas:**
```python
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    fullname: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    fullname: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
```

**Register Endpoint:**
```python
@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Hash password
    hashed_password = hash_password(user_data.password)
    
    # 3. Create user
    new_user = User(
        email=user_data.email,
        fullname=user_data.fullname,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 4. Generate JWT token
    access_token = create_access_token(data={"sub": new_user.email, "user_id": new_user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }
```

**Login Endpoint:**
```python
@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    # 1. Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 2. Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 3. Generate JWT token
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
```

**Get Current User:**
```python
@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_active_user)):
    return current_user
```

**Security Utilities (backend/core/security.py):**
```python
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), 
                     db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user
```

**Implementation tasks:**
1. Create User database model (SQLAlchemy)
2. Create Pydantic schemas (UserRegister, UserLogin, UserResponse, TokenResponse)
3. Implement password hashing with bcrypt (passlib)
4. Implement password verification
5. Generate JWT tokens with 7-day expiration
6. Create register endpoint with email validation
7. Create login endpoint with password verification
8. Create get current user endpoint
9. Add authentication middleware (HTTPBearer)
10. Handle errors (duplicate email, invalid credentials)
11. Add email format validation
12. Add password strength validation (min 6 characters)

---

### 4.3 Feature: Keyword Management

**File:** `backend/api/keywords.py`

**Endpoints:**
- `POST /api/keywords` - Add new keyword
- `GET /api/keywords` - Get user's keywords
- `DELETE /api/keywords/{id}` - Remove keyword

**Implementation tasks:**
1. Create CRUD operations for keywords table
2. Validate keyword uniqueness per user
3. Add authorization checks
4. Return proper error messages

---

### 4.4 Feature: LlamaIndex Integration

**File:** `backend/services/llama_service.py`

**Core functionality:**
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.openai import OpenAI

class LlamaService:
    def __init__(self):
        self.llm = OpenAI(model="gpt-4", temperature=0.1)
        self.index = None
        
    def load_documents(self, date_str: str):
        """Load .txt files from output/{date}/ folder"""
        import os
        from pathlib import Path
        
        path = f"./TrendNews/output/{date_str}/txt/"
        
        # Get the latest .txt file by name (sorted alphabetically/chronologically)
        txt_files = sorted(Path(path).glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError(f"No .txt files found in {path}")
        
        latest_file = txt_files[-1]  # Get the last file (latest by name)
        print(f"Loading latest file: {latest_file}")
        
        # Load only the latest file
        documents = SimpleDirectoryReader(input_files=[str(latest_file)]).load_data()
        
        # Create vector index
        self.index = VectorStoreIndex.from_documents(
            documents,
            node_parser=SentenceSplitter(chunk_size=512)
        )
        
    def query(self, question: str) -> str:
        """Query the indexed documents"""
        query_engine = self.index.as_query_engine(llm=self.llm)
        response = query_engine.query(question)
        return str(response)
        
    def summarize_by_keywords(self, keywords: list[str]) -> dict:
        """Generate summary filtered by keywords"""
        summaries = {}
        for keyword in keywords:
            prompt = f"Summarize all news related to '{keyword}'. Include original links if available."
            summary = self.query(prompt)
            summaries[keyword] = summary
        return summaries
```

**Implementation tasks:**
1. Install llama-index and dependencies
2. Configure LLM (OpenAI/local model)
3. Implement document loading from date folder
4. Create vector index with embeddings
5. Build query engine
6. Add keyword-based filtering
7. Extract source links from documents
8. Handle errors (missing files, API limits)

---

### 4.5 Feature: Daily Summary Generation

**File:** `backend/services/summary_service.py`

**Core functionality:**
```python
from datetime import datetime
from .llama_service import LlamaService

class SummaryService:
    def __init__(self, db_session, llama_service: LlamaService):
        self.db = db_session
        self.llama = llama_service
        
    async def generate_daily_summary(self, user_id: int, date: datetime):
        """Generate summary for user's keywords (on-demand)"""
        # 1. Check if thread already exists for today
        existing_thread = self.db.query(Threads).filter_by(
            user_id=user_id,
            date=date.date()
        ).first()
        
        if existing_thread:
            return existing_thread  # Return cached thread
        
        # 2. Get user's keywords
        keywords = self.db.query(Keywords).filter_by(user_id=user_id).all()
        
        if not keywords:
            return None  # No keywords, no summary
        
        # 3. Load documents for the date
        date_str = date.strftime("%Y年%m月%d日")  # Match folder format
        self.llama.load_documents(date_str)
        
        # 4. Generate summaries
        summaries = self.llama.summarize_by_keywords(
            [k.keyword for k in keywords]
        )
        
        # 5. Create thread
        thread = self.create_thread(user_id, date, summaries)
        
        return thread
        
    def create_thread(self, user_id: int, date: datetime, summaries: dict):
        """Create thread with summary message"""
        # Create thread
        thread = Threads(
            user_id=user_id,
            title=f"Daily Summary - {date.strftime('%Y-%m-%d')}",
            date=date.date()
        )
        self.db.add(thread)
        self.db.flush()
        
        # Create system message with summary
        content = self.format_summary(summaries)
        message = Messages(
            thread_id=thread.id,
            role="assistant",
            content=content,
            metadata={"summaries": summaries}
        )
        self.db.add(message)
        self.db.commit()
        
        return thread
        
    def format_summary(self, summaries: dict) -> str:
        """Format summaries into readable text"""
        lines = ["# Daily News Summary\n"]
        for keyword, summary in summaries.items():
            lines.append(f"## {keyword}\n")
            lines.append(f"{summary}\n\n")
        return "\n".join(lines)
```

**Implementation tasks:**
1. Check if thread exists for today (cache)
2. Return existing thread if available
3. Query user keywords from database
4. Return null if no keywords
5. Load documents for specific date
6. Generate summaries using LlamaIndex
7. Create thread in database
8. Store summary as first message
9. Extract and store metadata (links)
10. Handle edge cases (no data, no keywords)

---

### 4.6 Feature: Thread Management

**File:** `backend/api/threads.py`

**Endpoints:**
- `GET /api/threads` - Get user's threads (paginated)
- `GET /api/threads/today` - Get or generate today's summary thread
- `GET /api/threads/{id}` - Get thread with messages
- `DELETE /api/threads/{id}` - Delete thread

**Implementation tasks:**
1. Query threads by user_id
2. Include message count and preview
3. Pagination support
4. Sort by date (newest first)
5. Authorization checks
6. Generate today's summary on-demand if not exists

---

### 4.7 Feature: Chat Q&A

**File:** `backend/api/query.py`

**Endpoints:**
- `POST /api/threads/{id}/query` - Ask question in thread context

**Request body:**
```json
{
    "question": "What are the main points about AI regulation?"
}
```

**Response:**
```json
{
    "answer": "The main points about AI regulation include...",
    "sources": ["link1", "link2"],
    "message_id": 123
}
```

**Implementation tasks:**
1. Validate thread ownership
2. Load thread's date documents
3. Query LlamaIndex with question
4. Save user message to database
5. Save assistant response to database
6. Return answer with sources
7. Stream response support (optional)

---

## 5. Frontend Implementation

### 5.1 Project Structure
```
AnswerMe/
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── .env.local
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx           # Landing page
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── register/
│   │   │   │   └── page.tsx
│   │   │   └── dashboard/
│   │   │       ├── page.tsx       # Main dashboard
│   │   │       ├── settings/
│   │   │       │   └── page.tsx   # Keywords & schedule
│   │   │       └── thread/[id]/
│   │   │           └── page.tsx   # Thread chat view
│   │   ├── components/
│   │   │   ├── ui/               # shadcn components
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   ├── keywords/
│   │   │   │   ├── KeywordList.tsx
│   │   │   │   └── KeywordInput.tsx
│   │   │   ├── threads/
│   │   │   │   ├── ThreadList.tsx
│   │   │   │   └── ThreadItem.tsx
│   │   │   └── chat/
│   │   │       ├── ChatInterface.tsx
│   │   │       ├── MessageList.tsx
│   │   │       └── MessageInput.tsx
│   │   ├── lib/
│   │   │   ├── api.ts            # API client
│   │   │   └── utils.ts
│   │   └── store/
│   │       ├── authStore.ts      # Zustand auth state
│   │       ├── keywordStore.ts
│   │       └── threadStore.ts
```

### 5.2 Feature: Authentication UI

**Files:** 
- `src/components/auth/LoginForm.tsx`
- `src/components/auth/RegisterForm.tsx`
- `src/store/authStore.ts`
- `src/lib/api.ts`

**Zustand Auth Store (src/store/authStore.ts):**
```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  email: string
  fullname: string
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, fullname: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User, token: string) => void
}

export const useAuthStore = create<AuthState>()(persist(
  (set) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    
    login: async (email: string, password: string) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Login failed')
      }
      
      const data = await response.json()
      set({ user: data.user, token: data.access_token, isAuthenticated: true })
    },
    
    register: async (email: string, fullname: string, password: string) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, fullname, password }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Registration failed')
      }
      
      const data = await response.json()
      set({ user: data.user, token: data.access_token, isAuthenticated: true })
    },
    
    logout: () => {
      set({ user: null, token: null, isAuthenticated: false })
    },
    
    setUser: (user: User, token: string) => {
      set({ user, token, isAuthenticated: true })
    },
  }),
  {
    name: 'auth-storage',
  }
))
```

**Login Form (src/components/auth/LoginForm.tsx):**
```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function LoginForm() {
  const router = useRouter()
  const login = useAuthStore((state) => state.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="you@example.com"
        />
      </div>
      
      <div>
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          placeholder="••••••••"
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </Button>
    </form>
  )
}
```

**Register Form (src/components/auth/RegisterForm.tsx):**
```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function RegisterForm() {
  const router = useRouter()
  const register = useAuthStore((state) => state.register)
  const [email, setEmail] = useState('')
  const [fullname, setFullname] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)

    try {
      await register(email, fullname, password)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="you@example.com"
        />
      </div>
      
      <div>
        <Label htmlFor="fullname">Full Name</Label>
        <Input
          id="fullname"
          type="text"
          value={fullname}
          onChange={(e) => setFullname(e.target.value)}
          required
          minLength={2}
          placeholder="John Doe"
        />
      </div>

      <div>
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          placeholder="••••••••"
        />
      </div>

      <div>
        <Label htmlFor="confirmPassword">Confirm Password</Label>
        <Input
          id="confirmPassword"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          minLength={6}
          placeholder="••••••••"
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? 'Creating account...' : 'Register'}
      </Button>
    </form>
  )
}
```

**Protected Route Wrapper:**
```typescript
// src/components/auth/ProtectedRoute.tsx
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}
```

**Implementation tasks:**
1. Install shadcn/ui components (Button, Input, Label, Alert)
2. Create Zustand auth store with persist middleware
3. Implement login form with email/password fields
4. Implement register form with email/fullname/password/confirm fields
5. Add form validation (email format, password length, password match)
6. Add loading states during API calls
7. Add error handling and display
8. Store JWT token in localStorage via Zustand persist
9. Create protected route wrapper component
10. Auto-redirect to dashboard after successful auth
11. Auto-redirect to login if not authenticated
12. Add logout functionality

---

### 5.3 Feature: Keyword Management UI

**Files:**
- `src/components/keywords/KeywordList.tsx`
- `src/components/keywords/KeywordInput.tsx`
- `src/store/keywordStore.ts`

**UI Components:**
1. Input field to add keyword
2. List of current keywords (with delete button)
3. Tag-style display
4. Add/remove animations
5. Error handling (duplicates, API errors)

**Implementation tasks:**
1. Create keyword input component
2. Display keyword list with delete option
3. Setup Zustand keyword store
4. API integration (add/remove)
5. Optimistic updates
6. Loading states

---

### 5.4 Feature: Thread List UI

**Files:**
- `src/components/threads/ThreadList.tsx`
- `src/components/threads/ThreadItem.tsx`
- `src/store/threadStore.ts`

**UI Components:**
1. List of threads (sorted by date)
2. Each thread shows:
   - Date
   - Preview of summary
   - Message count
3. Click to open thread
4. Infinite scroll/pagination
5. Delete thread option

**Implementation tasks:**
1. Fetch threads from API
2. Display in card/list format
3. Pagination support
4. Click handler to navigate
5. Delete confirmation dialog
6. Loading skeleton
7. Empty state

---

### 5.5 Feature: Chat Interface UI

**Files:**
- `src/components/chat/ChatInterface.tsx`
- `src/components/chat/MessageList.tsx`
- `src/components/chat/MessageInput.tsx`

**UI Components:**
1. Message list (system summary + chat history)
2. Message bubbles (user vs assistant)
3. Original links in summary
4. Text input for questions
5. Send button
6. Loading indicator while AI responds

**Implementation tasks:**
1. Fetch thread messages
2. Display messages in chat format
3. Render markdown in messages
4. Extract and display links
5. Input component with send
6. Handle message submission
7. Optimistic updates
8. Scroll to bottom on new message
9. Loading states
10. Error handling

---

## 6. System Flow Diagram

```mermaid
flowchart TD
    Start([User truy cập app]) --> Input[Nhập keywords + chủ đề quan tâm]
    Input --> SaveDB[(Lưu vào PostgreSQL<br/>user info, keywords)]
    
    SaveDB --> DailyCrawl[Crawler chạy 6h sáng hàng ngày<br/>thu thập tin tức vào folder output/date/]
    
    DailyCrawl --> UserVisit[User vào trang dashboard]
    UserVisit --> CheckThread{Thread hôm nay<br/>đã tồn tại?}
    
    CheckThread -->|Có| ReturnThread[Trả về thread có sẵn]
    CheckThread -->|Không| LoadDocs[Load file .txt mới nhất]
    
    LoadDocs --> LlamaIndex[LlamaIndex xử lý<br/>- Create VectorStoreIndex<br/>- Build query engine]
    
    LlamaIndex --> Filter[Lọc tin tức theo keywords]
    Filter --> Summary[AI Summary tin tức<br/>liên quan đến keywords]
    
    Summary --> CreateThread[Tạo thread chat mới<br/>lưu vào DB]
    CreateThread --> ReturnThread
    ReturnThread --> UserView[Hiển thị summary cho user]
    UserView --> Read{Đọc summary}
    
    Read -->|Muốn chi tiết| Link[Click original link]
    Read -->|Có câu hỏi| Chat[Chat thêm trong thread]
    
    Chat --> Query[Gửi query đến backend]
    Query --> QueryEngine[LlamaIndex query engine<br/>trả lời câu hỏi]
    QueryEngine --> Response[Hiển thị câu trả lời<br/>trong thread chat]
    
    Response --> UserView
    Link --> External[Mở trang tin tức gốc]
    
    style Start fill:#e1f5ff
    style SaveDB fill:#fff4e1
    style LlamaIndex fill:#e8f5e9
    style Thread fill:#f3e5f5
    style UserView fill:#e1f5ff
```

---

## 7. Implementation Roadmap

### Phase 1: Backend Foundation (Week 1)
- [ ] Setup FastAPI project structure
- [ ] Configure PostgreSQL database
- [ ] Create database models and migrations
- [ ] Implement user authentication (JWT)
- [ ] Create keyword management API

### Phase 2: LlamaIndex Integration (Week 2)
- [ ] Setup LlamaIndex with document loading
- [ ] Implement vector indexing
- [ ] Create query engine
- [ ] Build summary generation service
- [ ] Add keyword filtering logic
- [ ] Extract source links from documents

### Phase 3: On-Demand Summary Generation (Week 2)
- [ ] Implement thread existence check
- [ ] Add GET /api/threads/today endpoint
- [ ] Generate summary only when user requests
- [ ] Cache thread to avoid regeneration
- [ ] Handle empty keywords gracefully
- [ ] Test on-demand generation flow

### Phase 4: Chat Q&A API (Week 3)
- [ ] Create thread management endpoints
- [ ] Implement chat query endpoint
- [ ] Add message history retrieval
- [ ] Test Q&A with LlamaIndex
- [ ] Add streaming support (optional)

### Phase 5: Frontend Setup (Week 3)
- [ ] Initialize Next.js project
- [ ] Setup TailwindCSS and shadcn/ui
- [ ] Configure Zustand stores
- [ ] Create API client with auth
- [ ] Build authentication pages

### Phase 6: Frontend Features (Week 4)
- [ ] Implement keyword management UI
- [ ] Create thread list view
- [ ] Build chat interface
- [ ] Add markdown rendering
- [ ] Polish UI/UX

### Phase 7: Integration & Testing (Week 5)
- [ ] Connect frontend to backend
- [ ] End-to-end testing
- [ ] Fix bugs and edge cases
- [ ] Performance optimization
- [ ] Add error handling

### Phase 8: Deployment (Week 5-6)
- [ ] Setup production environment
- [ ] Configure environment variables
- [ ] Deploy backend (Docker/Cloud)
- [ ] Deploy frontend (Vercel/Netlify)
- [ ] Setup monitoring and logs

---

## 8. Technical Requirements

### 8.1 Environment Variables

**Backend (.env):**
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/newsdb
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
OPENAI_API_KEY=sk-...
NEWS_DATA_PATH=../TrendNews/output
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 8.2 Dependencies

**Backend requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
llama-index==0.9.14
openai==1.3.7
python-dotenv==1.0.0
```

**Frontend package.json:**
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.4.6",
    "axios": "^1.6.0",
    "tailwindcss": "^3.3.0",
    "@radix-ui/react-*": "latest",
    "lucide-react": "^0.292.0",
    "react-markdown": "^9.0.0"
  }
}
```

---

## 9. API Documentation

### Authentication

#### `POST /api/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "fullname": "John Doe",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "fullname": "John Doe",
    "created_at": "2025-11-27T10:00:00Z"
  }
}
```

**Errors:**
- `400`: Email already registered
- `422`: Validation error (invalid email format, password too short)

#### `POST /api/auth/login`
Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "fullname": "John Doe",
    "created_at": "2025-11-27T10:00:00Z"
  }
}
```

**Errors:**
- `401`: Invalid email or password

#### `GET /api/auth/me`
Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "fullname": "John Doe",
  "created_at": "2025-11-27T10:00:00Z"
}
```

**Errors:**
- `401`: Invalid or expired token

### Keywords
- `POST /api/keywords` - Add keyword
- `GET /api/keywords` - List keywords
- `DELETE /api/keywords/{id}` - Delete keyword

### Threads
- `GET /api/threads` - List threads
- `GET /api/threads/{id}` - Get thread details
- `DELETE /api/threads/{id}` - Delete thread

### Chat
- `POST /api/threads/{id}/query` - Ask question
- `GET /api/threads/{id}/messages` - Get messages

---

## 10. Testing Strategy

### Backend Tests
- Unit tests for services
- Integration tests for API endpoints
- Test LlamaIndex integration
- Test on-demand summary generation
- Test thread caching

### Frontend Tests
- Component tests (Jest + React Testing Library)
- E2E tests (Playwright)
- API integration tests

---

## 11. Future Enhancements

- [ ] Multi-language support
- [ ] Email/Telegram notifications
- [ ] Export threads to PDF
- [ ] Keyword suggestions based on trending topics
- [ ] Analytics dashboard
- [ ] Mobile app (React Native)
- [ ] Voice input for queries
- [ ] Collaborative threads (share with team)

---

## 12. Reference Code Example

### LlamaIndex Basic Implementation
```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Load documents from crawled data
documents = SimpleDirectoryReader("./output/{current day}/{file .txt mới nhất}").load_data()

# Create vector index
index = VectorStoreIndex.from_documents(documents)

# Create query engine
query_engine = index.as_query_engine()

# Query
response = query_engine.query("What did the author do growing up?")
print(response)
```

Source: https://developers.llamaindex.ai/python/framework/understanding/putting_it_all_together/q_and_a#semantic-search

---

## Overview
Build chatbot summary tin tức từ các file .txt crawl được hàng ngày, sử dụng Llama Index để trả lời các truy vấn của người dùng. Khuynh hướng dùng giống feedly, lưu keyword người dùng quan tâm, summary các tin tức liên quan đến keyword đó để người dùng có thể đọc nhanh hằng ngày.

## Backend
- Tìm hiểu llama index , cách tích hợp làm chatbot summary tin tức từ các nguồn tin (*.txt) crawl được (từ folder outputs/{current day}/{file .txt mới nhất}) để trả lời query của người dùng . 
- Code example: 
```
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("./output/{current day}/{file .txt mới nhất}").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What did the author do growing up?")
print(response)  . 

```
From source (https://developers.llamaindex.ai/python/framework/understanding/putting_it_all_together/q_and_a#semantic-search) . 

## Các kĩ thuật frontend sử dụng.
- Use (vite + nextjs) for UI, shacdn , zudtate for state management, tailwindcss for styling.
- UI gồm 1 input để user nhập query, 1 button submit, 1 div để show kết quả trả lời từ chatbot.

## Các kĩ thuật backend.
- Use fastapi for backend server, uvicorn as server runner.
- Use llama index để làm chatbot summary tin tức từ các file .txt crawl được hàng ngày
- Dùng postgres để save user info, keyword user quan tâm, thời điểm user muốn nhận report hằng ngày.

## Context code (backend python + frontend nextjs)
AnswerMe