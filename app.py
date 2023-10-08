import re
import random
from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,JSONResponse, RedirectResponse, Response
import requests
import mysql.connector
from mysql.connector import Error
from fuzzywuzzy import fuzz
from transformers import pipeline
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
from typing import List
from fastapi import Cookie
from starlette.routing import Route
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import speech_recognition as sr

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Intent classification API
classification_pipe = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
candidate_labels = [
    "account",
    "home",
    "products",
    "cart", "product's price high to low","product's price low to high", "add product to cart",
    "remove from cart","product's details information","increase item quantity in cart","decrease item quantity in cart","log out"
]

fake_users_db = {}

class VoiceInput(BaseModel):
    command: str

recognizer = sr.Recognizer()
# OAuth2 authentication
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str

# OAuth2PasswordBearer for token validation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Establish a connection to the MySQL database
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='webgpt',
            user='root',
            password='1234'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

# Retrieve product data from the MySQL database
def get_products():
    try:
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, price FROM products")
            products = cursor.fetchall()
            cursor.close()
            return products
    except Error as e:
        print(f"Error retrieving products from MySQL database: {e}")
    finally:
        if connection is not None:
            connection.close()
    return []

# Retrieve a random subset of products from the MySQL database
def get_random_products(num_products=3):
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM products ORDER BY RAND() LIMIT %s", (num_products,))
    random_products = cursor.fetchall()
    cursor.close()
    connection.close()
    return random_products

# Modify the get_product function to query the product by ID from the MySQL database
def get_product(product_id: int):
    try:
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            cursor.close()
            if product is not None:
                return {
                    "id": product[0],
                    "name": product[1],
                    "price": product[2],
                    "description": product[3]
                }
    except Error as e:
        print(f"Error retrieving product from MySQL database: {e}")
    finally:
        if connection is not None:
            connection.close()
    return None

def get_cart(username: str):
    try:
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()

            # Get the user ID based on the username
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

            # Retrieve cart items for the user's cart
            cursor.execute("SELECT uc.product_id, p.name, p.price, uc.quantity FROM user_carts uc JOIN products p ON uc.product_id = p.id WHERE uc.user_id = %s", (user_id,))
            cart_items = cursor.fetchall()

            cursor.close()
            connection.close()

            cart = []
            for product_id, name, price, quantity in cart_items:
                cart.append({
                    "product": {
                        "id": product_id,
                        "name": name,
                        "price": price,
                    },
                    "quantity": quantity
                })

            return cart
    except Error as e:
        print(f"Error retrieving cart items from MySQL database: {e}")
    return []

def update_item_quantity(product_id: int, quantity_change: int, user_id: int):
    connection = create_connection()
    cursor = connection.cursor()

    # Check if the product is in the user's cart
    cursor.execute("SELECT quantity FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    cart_item = cursor.fetchone()

    if cart_item:
        new_quantity = max(0, cart_item[0] + quantity_change)  # Ensure quantity doesn't go below 0
        if new_quantity > 0:
            cursor.execute("UPDATE user_carts SET quantity = %s WHERE user_id = %s AND product_id = %s", (new_quantity, user_id, product_id))
        else:
            cursor.execute("DELETE FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    else:
        error_message = "You don't have such product in your cart. Please mention the product name clearly."
        return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

    connection.commit()
    cursor.close()
    connection.close()

class SessionMiddlewareConfig(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        return response

app.add_middleware(SessionMiddleware, secret_key="1234")

# Middleware for authorization
def authorize_user(request: Request):
    if "username" not in request.session:
        return None
    return request.session["username"]

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
PASSWORD_REGEX = r'^(?=.*[a-zA-Z])(?=.*\d).{8,}$'

@app.route("/signup", methods=["GET", "POST"])
async def signup(request: Request):
    if request.method == "POST":
        form = await request.form()
        username = form.get("username")
        name = form.get("name")
        password = form.get("password")
        email = form.get("email")
        phone = form.get("phone")

        hashed_password = pwd_context.hash(password)

        if not re.match(PASSWORD_REGEX, password):
            return templates.TemplateResponse("signup.html", {"request": request, "message": "Password must be at least 8 characters and include both letters and numbers!"})
        
        if not re.match(EMAIL_REGEX, email):
            return templates.TemplateResponse("signup.html", {"request": request, "message": "Invalid email format!"})

        if not re.match(r'^\d{10}$', phone):
            return templates.TemplateResponse("signup.html", {"request": request, "message": "Phone number must be 10 digits!"})

        connection = create_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, email, phone, name) VALUES (%s, %s, %s, %s, %s)",
                           (username, hashed_password, email, phone, name))
            connection.commit()
        except mysql.connector.IntegrityError as err:
            if "unique_username" in str(err):
                return templates.TemplateResponse("signup.html", {"request": request, "message": "username already in use!"})
            elif "phone_UNIQUE" in str(err):
                return templates.TemplateResponse("signup.html", {"request": request, "message": "Phone number already in use!"})
            elif "email_UNIQUE" in str(err):
                return templates.TemplateResponse("signup.html", {"request": request, "message": "Email already in use!"})
            else:
                print("Database Error:", err)
                connection.rollback()
                raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            cursor.close()
            connection.close()

        return templates.TemplateResponse("login.html", {"request": request, "message": "User registered successfully"})

    return templates.TemplateResponse("signup.html", {"request": request})


# Login function
@app.route("/", methods=["GET", "POST"])
async def login(request: Request):
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def render_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Access Token Generation function (For illustration purposes)
@app.post("/token")
async def generate_token(request: Request,form_data: OAuth2PasswordRequestForm = Depends()):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (form_data.username,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if user and pwd_context.verify(form_data.password, user["password"]):
        response = RedirectResponse(url="/home", status_code=307)
        response.set_cookie(key="username", value=user["username"])
        return response
    error_message = "Invalid credentials! Please check and try again."
    return templates.TemplateResponse("login.html", {"request": request, "error_message": error_message})

@app.post("/logout")
async def logout(request: Request, response: Response):
    if "username" in request.session:
        del request.session["username"]

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.delete_cookie("username")
    
    return RedirectResponse(url="/login?rand=" + str(random.randint(1, 10000)), status_code=307)

# Home page
@app.route("/home", methods=["GET", "POST"])
async def home(request: Request):
    random_products = get_random_products(6)
    return templates.TemplateResponse("home.html", {"request": request, "random_products": random_products})

# Product list page
@app.get("/products")
def get_product_list(request: Request, sort: str = ""):
    products = get_products()

    if sort == "price_asc":
        sorted_products = sorted(products, key=lambda x: x[2])
    elif sort == "price_desc":
        sorted_products = sorted(products, key=lambda x: x[2], reverse=True)
    else:
        sorted_products = products

    # Retrieve the product details and add them to the sorted_products list
    product_details = []
    for product in sorted_products:
        product_id = product[0]
        product_detail = get_product(product_id)
        if product_detail:
            product_details.append(product_detail)

    return templates.TemplateResponse("products.html", {"request": request, "products": product_details})


# POST request for product list page
@app.post("/products")
def post_product_list(request: Request):
    return get_product_list(request)

@app.post("/display_sorted_products")
def display_sorted_products(request: Request, sort: str = "price_desc"):
    products = get_products()

    if sort == "price_asc":
        sorted_products = sorted(products, key=lambda x: x[2])
    elif sort == "price_desc":
        sorted_products = sorted(products, key=lambda x: x[2], reverse=True)
    else:
        sorted_products = products

    # Generate the list of product links
    product_links = [
        {
            "name": product[1],
            "price": product[2],
            "url": f"/products/{product[0]}"
        }
        for product in sorted_products
    ]

    return templates.TemplateResponse("popup.html", {"request": request, "products": product_links})

@app.get("/products/{product_id}")
def get_product_detail(request: Request, product_id: int):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse("product_detail.html", {"request": request, "product": product})

@app.post("/products/{product_id}")
def post_product_detail(request: Request, product_id: int):
    return get_product_detail(request, product_id)

# Cart page
@app.route("/cart", methods=["GET", "POST"])
async def view_cart(request: Request, token: str = Depends(oauth2_scheme)):
    # Retrieve the username from the cookies
    username = request.cookies.get("username")

    cart = get_cart(username)
    return templates.TemplateResponse("cart.html", {"request": request, "cart":cart})

@app.post("/add_to_cart", response_class=JSONResponse)
async def add_to_cart(request: Request):
    data = await request.json()
    product_id = data.get("product_id")
    if product_id is None:
        raise HTTPException(status_code=400, detail="Product ID not provided")

    # Check if the product exists in the products table
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Retrieve the username from the cookies
    username = request.cookies.get("username")

    connection = create_connection()
    cursor = connection.cursor()

    try:
        # Get the user ID based on the username
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cursor.fetchone()[0]

        # Update the quantity of an existing product in the user's cart
        cursor.execute("UPDATE user_carts SET quantity = quantity + 1 WHERE user_id = %s AND product_id = %s", (user_id, product_id))

        # If the product is not in the cart, insert a new row
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO user_carts (user_id, product_id, quantity) VALUES (%s, %s, 1)", (user_id, product_id))

        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return {"message": f"Product with ID {product_id} added to cart"}

@app.post("/remove_from_cart", response_class=JSONResponse)
async def remove_from_cart(request: Request):
    data = await request.json()
    product_id = data.get("product_id")
    if product_id is None:
        raise HTTPException(status_code=400, detail="Product ID not provided")

    # Retrieve the username from the cookies
    username = request.cookies.get("username")

    connection = create_connection()
    cursor = connection.cursor()

    try:
        # Get the user ID based on the username
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cursor.fetchone()[0]

        # Check if the product is in the user's cart
        cursor.execute("SELECT quantity FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        cart_item = cursor.fetchone()

        if cart_item:
            quantity = cart_item[0]
            if quantity > 1:
                # If quantity is more than 1, update the quantity in the cart
                cursor.execute("UPDATE user_carts SET quantity = %s WHERE user_id = %s AND product_id = %s", (quantity - 1, user_id, product_id))
            else:
                # If quantity is 1, remove the product from the user's cart
                cursor.execute("DELETE FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))

            connection.commit()
    finally:
        cursor.close()
        connection.close()

    return {"message": "Product removed from cart"}

@app.route("/account", methods=["GET", "POST"])
async def account(request: Request, token: str = Depends(oauth2_scheme)):
    # Retrieve the username from the cookies
    username = request.cookies.get("username")

    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Retrieve user information based on the username
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if user:
        return templates.TemplateResponse("account.html", {"request": request, "user": user})
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/voice/")
async def voice_to_text(input_data: VoiceInput):
    if input_data.command == 'start':
        with sr.Microphone() as source:
            print("Adjusting noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Recording...")

            audio_stream = recognizer.listen(source, timeout=None)  # Listen indefinitely

            print("Done recording.")
            try:
                print("Recognizing the text...")
                text = recognizer.recognize_google(audio_stream, language="en-US")
                return {"message": text}
            except sr.UnknownValueError:
                return {"message": "Google Speech Recognition could not understand the audio."}
            except sr.RequestError:
                return {"message": "Could not request results from Google Speech Recognition service."}
            except Exception as ex:
                return {"message": f"Error during recognition: {ex}"}

# Process instruction
@app.post("/process_instruction", response_class=RedirectResponse)
async def process_instruction(request: Request, instruction: str = Form(...)):
    
    instruction = instruction.lower()
    classification_result = classification_pipe(instruction, candidate_labels)
    max_index = classification_result['scores'].index(max(classification_result['scores']))
    intent = classification_result['labels'][max_index]
    print("Intent:", intent)

    if intent == "account":
        # Redirect to the account page
        return RedirectResponse(url="/account")
    elif intent == "home":
        # Redirect to the home page
        return RedirectResponse(url="/home")
    elif intent == "products":
        # Redirect to the product list page
        return RedirectResponse(url="/products")
    elif intent == "cart":
        # Redirect to the cart page
        return RedirectResponse(url="/cart")
    elif intent == "product's price high to low":
        # Display sorted products in a popup box (descending order)
        return RedirectResponse(url="/display_sorted_products?sort=price_desc")
    elif intent == "product's price low to high":
        # Display sorted products in a popup box (ascending order)
        return RedirectResponse(url="/display_sorted_products?sort=price_asc")
    elif intent == "add product to cart":
    # Extract the product ID from the instruction
        product_id = extract_product_id(instruction)
        if product_id is None:
            error_message = "Seems we don't have a product similar to what you mentioned. Can you be more clear in your instruction?"
            return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

    # Check if the product exists in the products table
        product = get_product(product_id)
        if not product:
            error_message = "Seems we don't have a product similar to what you mentioned. Can you be more clear in your instruction?"
            return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

        connection = create_connection()
        cursor = connection.cursor()

    # Retrieve the username from the cookies
        username = request.cookies.get("username")

        try:
        # Get the user ID based on the username
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

        # Check if the product is already in the user's cart
            cursor.execute("SELECT quantity FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))
            cart_item = cursor.fetchone()

            if cart_item:
            # If the product is in the cart, increment the quantity
                quantity = cart_item[0] + 1
                cursor.execute("UPDATE user_carts SET quantity = %s WHERE user_id = %s AND product_id = %s", (quantity, user_id, product_id))
            else:
            # If the product is not in the cart, add it to the cart with quantity 1
                cursor.execute("INSERT INTO user_carts (user_id, product_id, quantity) VALUES (%s, %s, 1)", (user_id, product_id))

            connection.commit()
        finally:
            cursor.close()
            connection.close()

        return RedirectResponse(url="/cart", status_code=307)

    elif intent == "remove from cart":
    # Extract the product ID from the instruction
        product_id = extract_product_id(instruction)
        if product_id is None:
            error_message = "You don't have such product in your cart. Please mention the product name accurately."
            return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

        connection = create_connection()
        cursor = connection.cursor()

    # Retrieve the username from the cookies
        username = request.cookies.get("username")

        try:
        # Get the user ID based on the username
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

        # Check if the product is in the user's cart
            cursor.execute("SELECT quantity FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))
            cart_item = cursor.fetchone()

            if cart_item:
            # If the product is in the cart and its quantity is more than 1, decrement the quantity
                if cart_item[0] > 1:
                    quantity = cart_item[0] - 1
                    cursor.execute("UPDATE user_carts SET quantity = %s WHERE user_id = %s AND product_id = %s", (quantity, user_id, product_id))
                else:
                # If the product is in the cart and its quantity is 1, remove it from the cart
                    cursor.execute("DELETE FROM user_carts WHERE user_id = %s AND product_id = %s", (user_id, product_id))
            else:
                error_message = "You don't have such product in your cart. Please mention the product name clearly."
                return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

            connection.commit()
        finally:
            cursor.close()
            connection.close()

        return RedirectResponse(url="/cart", status_code=307)
    
    elif intent == "increase item quantity in cart":
        # Extract the product name and quantity from the instruction
        product_id, quantity_change = extract_product_id_and_quantity(instruction)
        if product_id is None or quantity_change is None:
            error_message = "Sorry, I couldn't understand the product or the quantity change. Can you please provide more information?"
            return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

        # Retrieve the username from the cookies
        username = request.cookies.get("username")

        connection = create_connection()
        cursor = connection.cursor()

        try:
            # Get the user ID based on the username
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

            # Increase the quantity of the specified product in the user's cart
            update_item_quantity(product_id, quantity_change, user_id)
        finally:
            cursor.close()
            connection.close()

        return RedirectResponse(url="/cart", status_code=307)

    elif intent == "decrease item quantity in cart":
        # Extract the product name and quantity from the instruction
        product_id, quantity_change = extract_product_id_and_quantity(instruction)
        if product_id is None or quantity_change is None:
            error_message = "Sorry, I couldn't understand the product or the quantity change. Can you please provide more information?"
            return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))

        # Retrieve the username from the cookies
        username = request.cookies.get("username")

        connection = create_connection()
        cursor = connection.cursor()

        try:
            # Get the user ID based on the username
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

            # Decrease the quantity of the specified product in the user's cart
            update_item_quantity(product_id, -quantity_change, user_id)
        finally:
            cursor.close()
            connection.close()

        return RedirectResponse(url="/cart", status_code=307)

    elif intent == "product's details information":
        # Extract the product name from the instruction
        product_id = extract_product_id(instruction)
        if product_id is None:
            error_message = "Seems we dont have a product similar to what you mentioned. Can you be more clear in your instruction."
            return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))
        # Redirect to the individual product page
        return RedirectResponse(url=f"/products/{product_id}")
    
    elif intent == "log out":
        return RedirectResponse(url="/logout")

    else:
        error_message = "Sorry I don't get what you say. Can you be more accurate."
        return HTMLResponse(content=templates.get_template("error_popup.html").render(error_message=error_message))
    

def extract_product_id(instruction: str):
    try:
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT id, name FROM products")
            products_data = cursor.fetchall()
            cursor.close()
    except Error as e:
        print(f"Error retrieving products data from MySQL database: {e}")
    finally:
        if connection is not None:
            connection.close()

    best_match_ratio = 0
    best_match_product_id = None

    for product_id, product_name in products_data:
        similarity_ratio = fuzz.partial_ratio(product_name.lower(), instruction.lower())
        if similarity_ratio > best_match_ratio:
            best_match_ratio = similarity_ratio
            best_match_product_id = product_id

    # Adjust the threshold as per your requirement
    if best_match_ratio > 70:
        return best_match_product_id

    return None

def extract_product_id_and_quantity(instruction: str):
    try:
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT id, name FROM products")
            products_data = cursor.fetchall()
            cursor.close()
    except Error as e:
        print(f"Error retrieving products data from MySQL database: {e}")
    finally:
        if connection is not None:
            connection.close()

    best_match_ratio = 0
    best_match_product_id = None

    for product_id, product_name in products_data:
        similarity_ratio = fuzz.partial_ratio(product_name.lower(), instruction.lower())
        if similarity_ratio > best_match_ratio:
            best_match_ratio = similarity_ratio
            best_match_product_id = product_id

    # Adjust the threshold as per your requirement
    if best_match_ratio > 70:
        # Extract quantity from the instruction
        quantity = None
        words = instruction.split()
        for word in words:
            if word.isdigit():
                quantity = int(word)
                break

        return best_match_product_id, quantity

    return None, None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)