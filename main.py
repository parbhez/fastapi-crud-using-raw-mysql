from fastapi import FastAPI, HTTPException, status, Query
import mysql.connector 
from mysql.connector import Error
from pydantic import BaseModel, EmailStr, ValidationError, Field
from datetime import datetime
from typing import Optional
import json
from knowledge_search import search_from_wikipedia_action_api, search_google_news_with_content, search_linkedin_duckduckgo
from enum import Enum

app = FastAPI()

# Enum Class
class SupportedLanguages(str, Enum):
    bangla = "bn"
    english = "en"
    hindi = "hi"
    urdu = "ur"
    arabic = "ar"



#====================================Intelligent Search System=============================

@app.get("/ask/")

def ask_question(
    q: str = Query(..., description="Type your question"),
    ln: SupportedLanguages = Query(..., description="Select language")
):
    wiki_result  = search_from_wikipedia_action_api(q, lang=ln.value)
    news_results   = search_google_news_with_content(q, lang=ln.value)
    linkedin_results   = search_linkedin_duckduckgo(q, lang=ln.value)

    return {
        "status": "success",
        "query": q,
        "wikipedia": {
            "title": wiki_result['title'],
            "answer": wiki_result['extract'],
            "source": wiki_result['source']
        },
        "google_news": news_results,  # List of articles
        "linkedin_results": linkedin_results  # List of linkedin result
    }



# Database connection function
def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="fastapi_db"
    )
    return connection

@app.get("/mysql_connection_check")
def mysql_connection_check():
    conn = get_connection()

    try:
        if conn.is_connected():
            db_info = conn.get_server_info()
            conn.close()
            return {"message": f"Connected to mysql server version {db_info}"}
    except Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database connection failed {str(e)}")


# Pydantic Model 
class User(BaseModel):
    # id: int
    name: str
    email: EmailStr
    status: bool = True 
    phone: Optional[str] = None # # নতুন phone ফিল্ড, অপশনাল (না দিলে চলবে)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    #Default আচরণ: অতিরিক্ত ফিল্ড এলে 422 error
    class Config:
        extra = "ignore" # অতিরিক্ত অজানা ফিল্ড হলে ইগনোর করবে or silently বাদ দিবে
        #extra = "allow" # দিলে নেবে, কিন্তু validation করবে না


# ===================================== CRUD ROUTES =======================================

# Create User
@app.post("/users")
async def create_user(user: User):

    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO users (name, email, status, phone, created_at) values(%s, %s, %s, %s, %s)"
        cursor.execute(sql, (user.name, user.email, user.status, user.phone, user.created_at))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {
            "status": "success",
            "message": "User inserted successfully",
            "code": status.HTTP_201_CREATED,
            "last_row_id": user_id,
            "data": user,
        }
    except Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "status": "error",
            "message": f"Mysql Error: {str(e)}",
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "data": []
        })

# Read All User
@app.get("/users")
def get_all_users():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        conn.close()

        return {
            "status": "success",
            "message": "User list fetch successfully",
            "code": status.HTTP_200_OK,
            "data": users
        }
    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"Mysql Error: {str(e)}",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "data": []
            }
        )
    

# Read Specific user
@app.get("/users/{user_id}")
async def read_one(user_id: int):
    # print(type(user_id))
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM users WHERE id=%s"
        cursor.execute(sql, (user_id,))  # <-- note the comma to make it a tuple
        user = cursor.fetchone()
        conn.close()

        return {
            "status": "success",
            "message": "User fetched successfully",
            "code": status.HTTP_200_OK,
            "data": user
        }

    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"MySQL Error: {str(e)}",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "data": []
            }
        )
    

# PUT route to update user
@app.put("/users/{user_id}")
async def update_user(user_id: int, user: User):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            UPDATE users 
            SET name = %s, email = %s, phone = %s, status = %s, updated_at = %s 
            WHERE id = %s
        """
        values = (
            user.name,
            user.email,
            user.phone,
            user.status,
            user.updated_at,
            user_id
        )

        cursor.execute(sql, values)
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": "User updated successfully",
            "code": status.HTTP_200_OK,
            "data": user
        }

    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"MySQL Error: {str(e)}",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "data": []
            }
        )


# Delete User
@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Optional: Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "User not found",
                    "code": status.HTTP_404_NOT_FOUND,
                    "data": []
                }
            )

        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": "User deleted successfully",
            "code": status.HTTP_200_OK,
            "data": result
        }

    except Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"MySQL Error: {str(e)}",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "data": []
            }
        )
