from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import *
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django import forms
from django.db.models import Q
import json
from django.http import JsonResponse
from cart.cart import Cart
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ObjectDoesNotExist
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import csv
from django.views.decorators.csrf import csrf_exempt
import logging 
from django.core.mail import send_mail
import random
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        myuser = Admin.objects.filter(email=email).first()
        if myuser is not None and myuser.check_password(password):
            login(request, myuser, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, "Login Successful!")
            return redirect('/admin1')
        else:
            messages.error(request, "Invalid Credentials!")
        return redirect('/admin_login')
    return render(request, "admin_login.html")

# @login_required
def admin1(request):
    categories = Category.objects.all()
    print(categories)
    return render(request, 'admin.html', {'categories': categories})


# save product from admin dashboard
def save_product(request):
    if request.method == 'POST':
        try:
            product_name = request.POST['productName']
            product_description = request.POST['productDescription']
            product_price = request.POST['productPrice']
            product_stock = request.POST['productStock']
            product_category_id = request.POST['productCategory']           
            product_category = Category.objects.filter(id=product_category_id).first()
            if not product_category:
                return JsonResponse({'success': False, 'error': f"Category with ID '{product_category_id}' does not exist."})
            product = Product(
                name=product_name,
                description=product_description,
                price=product_price,
                stock=product_stock,
                category=product_category
            )
            product.save()
            return render(request,"admin.html")
        except Exception as e:
            return render(request,"admin.html")
    else:
        return render(request,"admin.html")

def save_category(request):
    if request.method == 'POST':
        try:
            # Extract form data
            category_name = request.POST.get('categoryName')

            # Save the new category to the database
            category = Category(name=category_name)
            category.save()

            return render(request,"admin.html")
        except Exception as e:
            return render(request,"admin.html")
    else:
        return HttpResponse("Method not allowed", status=405)
    
def delete_product(request):
    if request.method == 'POST':
        try:
            product_name = request.POST['productName']
            product = Product.objects.filter(name=product_name).first()
            if not product:
                return JsonResponse({'success': False, 'error': f"Product with name '{product_name}' does not exist."})            
            product.delete()
            return render(request,"admin.html")
        except Exception as e:
            return render(request,"admin.html")
    else:
        return render(request,"admin.html")

def update_product(request):
    if request.method == 'POST':
        try:
            product_name = request.POST['productName']
            product_description = request.POST['productDescription']
            product_price = request.POST['productPrice']
            product_stock = request.POST['productStock']
            product_category_id = request.POST['productCategory'] 
            product = Product.objects.filter(name=product_name).first()
            if not product:
                return JsonResponse({'success': False, 'error': f"Product with name '{product_name}' does not exist."})
            category = Category.objects.filter(id=product_category_id).first()
            if not category:
                return JsonResponse({'success': False, 'error': f"Category with ID '{product_category_id}' does not exist."})            
            product.description = product_description
            product.price = product_price
            product.stock = product_stock
            product.category = category 
            product.save()
            return render(request,"admin.html")
        except Exception as e:
            return render(request,"admin.html")
    else:
        return render(request,"admin.html")
    
def show_product(request):
    products = Product.objects.all()
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Define styles for paragraphs with potential long texts
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    wrapped_style = ParagraphStyle('Wrapped', parent=styles['Normal'], wordWrap='CJK', fontSize=8, leading=10)
    
    # Prepare data for the table
    data = []
    data.append(["Name", "Description", "Price", "Stock", "Category"])
    
    for product in products:
        name = Paragraph(product.name, wrapped_style)
        description = Paragraph(product.description, wrapped_style)
        price = Paragraph(f"${product.price:.2f}", normal_style)
        stock = Paragraph(str(product.stock), normal_style)
        category = Paragraph(product.category.name, normal_style)
        
        data.append([name, description, price, stock, category])
    
    # Define column widths
    col_widths = [2.5 * inch, 2.5 * inch, 1 * inch, 1 * inch, 1.5 * inch]
    table = Table(data, colWidths=col_widths)
    
    # Style the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    
    # Build the PDF
    pdf.build([table])
    pdf_content = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="products.pdf"'
    response.write(pdf_content)
    
    return response

def download_product_excel(request):
    products = Product.objects.all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Products"
    
    # Define the headers
    headers = ["Name", "Description", "Price", "Stock", "Category"]
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        sheet[f'{col_letter}1'] = header
    
    # Populate the data
    for row_num, product in enumerate(products, 2):
        sheet[f'A{row_num}'] = product.name
        sheet[f'B{row_num}'] = product.description
        sheet[f'C{row_num}'] = product.price
        sheet[f'D{row_num}'] = product.stock
        sheet[f'E{row_num}'] = product.category.name
    
    # Create a response object and set the appropriate headers
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="products.xlsx"'
    
    # Save the workbook to the response
    workbook.save(response)
    
    return response

def download_product_csv(request):
    products = Product.objects.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'
    
    writer = csv.writer(response)
    writer.writerow(["Name", "Description", "Price", "Stock", "Category"])
    
    for product in products:
        writer.writerow([
            product.name, 
            product.description, 
            f"${product.price:.2f}", 
            product.stock, 
            product.category.name
        ])
    
    return response

def delete_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('categoryName')
        category = get_object_or_404(Category, name=category_name)
        category.delete()
        messages.success(request, 'Category deleted successfully.')
        return render(request,"admin.html")
    else:
        return render(request,"admin.html")
    
def show_category(request):
    categories = Category.objects.all()
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter)
    data = [["ID", "Name"]]
    for category in categories:
        data.append([category.id, category.name])
    table = Table(data)
    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)])
    table.setStyle(style)
    pdf.build([table])
    pdf_content = buffer.getvalue()
    buffer.close()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="categories.pdf"'
    response.write(pdf_content)
    return response

def show_category_csv(request):
    categories = Category.objects.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="categories.csv"'
    
    writer = csv.writer(response)
    writer.writerow(["ID", "Name"])
    
    for category in categories:
        writer.writerow([category.id, category.name])
    
    return response

def show_category_excel(request):
    categories = Category.objects.all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Categories"
    
    # Define the headers
    headers = ["ID", "Name"]
    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        sheet[f'{col_letter}1'] = header
    
    # Populate the data
    for row_num, category in enumerate(categories, 2):
        sheet[f'A{row_num}'] = category.id
        sheet[f'B{row_num}'] = category.name
    
    # Create a response object and set the appropriate headers
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="categories.xlsx"'
    
    # Save the workbook to the response
    workbook.save(response)
    
    return response

def search(request):
    if request.method == "POST":
        searched = request.POST['searched']
        # Query The Products DB Model
        searched_products = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
        # Test for null
        if not searched_products:
            messages.success(request, "That Product Does Not Exist...Please try Again.")
            return render(request, "search.html", {})
        else:
            return render(request, "search.html", {'searched':searched_products})
    else:
        return render(request, "search.html", {})


def update_info(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            shipping_form = ShippingForm(request.POST)
            if shipping_form.is_valid():
                # Save the shipping form
                shipping_address = shipping_form.save(commit=False)
                shipping_address.user = request.user
                shipping_address.save()

                # Update the Profile model with relevant data from the ShippingForm
                profile, created = Profile.objects.get_or_create(user=request.user)
                if created:
                    profile.address1 = shipping_form.cleaned_data.get('address1', '')
                    profile.address2 = shipping_form.cleaned_data.get('address2', '')
                    profile.city = shipping_form.cleaned_data.get('city', '')
                    profile.state = shipping_form.cleaned_data.get('state', '')
                    profile.zipcode = shipping_form.cleaned_data.get('zipcode', '')
                    profile.country = shipping_form.cleaned_data.get('country', '')
                    profile.save()

                messages.success(request, "Your Info Has Been Updated!!")
                return redirect('update_info')
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            shipping_form = ShippingForm()

        return render(request, "update_info.html", {'shipping_form': shipping_form})
    else:
        messages.error(request, "You Must Be Logged In To Access That Page!!")
        return redirect('home')


def update_password(request):
	if request.user.is_authenticated:
		current_user = request.user
		# Did they fill out the form
		if request.method  == 'POST':
			form = ChangePasswordForm(current_user, request.POST)
			# Is the form valid
			if form.is_valid():
				form.save()
				messages.success(request, "Your Password Has Been Updated...")
				login(request, current_user)
				return redirect('update_user')
			else:
				for error in list(form.errors.values()):
					messages.error(request, error)
					return redirect('update_password')
		else:
			form = ChangePasswordForm(current_user)
			return render(request, "update_password.html", {'form':form})
	else:
		messages.success(request, "You Must Be Logged In To View That Page...")
		return redirect('home')
# @login_required
# @require_POST
def update_user(request):
    if request.user.is_authenticated:
        try:
            current_user = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            messages.error(request, "Customer profile does not exist.")
            return redirect('home')
        
        if request.method == 'POST':
            user_form = UpdateUserForm(request.POST, instance=current_user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "User Has Been Updated!!")
                return redirect('home')
        else:
            user_form = UpdateUserForm(instance=current_user)
        
        return render(request, "update_user.html", {'user_form': user_form})
    else:
        messages.error(request, "You Must Be Logged In To Access That Page")
        return redirect('home')


def category_summary(request):
	categories = Category.objects.all()
	return render(request, 'category_summary.html', {"categories":categories})	

def category(request, foo):
    foo = foo.replace('-', ' ')
    try:
        category = Category.objects.get(name=foo)
        products = Product.objects.filter(category=category)        
        products_with_ratings = []
        for product in products:
            ratings = ProductRating.objects.filter(product=product)
            if ratings.exists():
                average_rating = ratings.aggregate(models.Avg('rating'))['rating__avg']
            else:
                average_rating = 0
            stars = ['filled' if i < average_rating else 'empty' for i in range(5)]
            products_with_ratings.append({
                'product': product,
                'stars': stars
            })
        for item in products_with_ratings:
            print(f" Stars: {item['stars']}")
        return render(request, 'category.html', {'products_with_ratings': products_with_ratings, 'category': category})
    except Category.DoesNotExist:
        messages.success(request, ("That Category Doesn't Exist..."))
        return redirect('home')


def product(request, pk):
    product = Product.objects.get(id=pk)
    
    sentences = product.description.split('.')
    
    # Construct an HTML list from the sentences, omitting empty sentences
    formatted_description = "<ul>" + "".join(f"<li>{sentence.strip()}.</li>" for sentence in sentences if sentence.strip()) + "</ul>"
    
    # Update the product description to the formatted HTML
    product.description = formatted_description
    return render(request, 'product.html', {'product': product})


def home(request):
	categories = Category.objects.all()
	return render(request, 'home.html', {'categories':categories})


def about(request):
	return render(request, 'about.html', {})	


def login(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password1")
        try:
            customer = Customer.objects.get(email=email)
            if check_password(password, customer.password):
                request.session['customer_id'] = customer.pk 
                messages.success(request, "Login Successful!")
                return redirect('/')
            else:
                messages.error(request, "Invalid Credentials!")
                return redirect('/login')
        except Customer.DoesNotExist:
            messages.error(request, "User doesn't exist")
            return redirect('/login')
    return render(request, "login.html")

def logout_user(request):
	logout(request)
	messages.success(request, ("You have been logged out...Thanks for stopping by..."))
	return redirect('home')

def register_user(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password1")
        password2 = request.POST.get("password2")
        if Customer.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose a different username.")
            return render(request, "register.html", {'error_message': ""})
        elif Customer.objects.filter(email=email).exists():
            messages.error(request, "Email already exists. Please Login")
            return render(request, "login.html")
        if password != password2:
            messages.error(request, "Both Passwords don't match")
            return render(request, "register.html", {'error_message': " "})        
        hashed_password = make_password(password)
        myuser = Customer(username=username, email=email, password=hashed_password)
        myuser.save()
        messages.success(request, "User created successfully!")
        return redirect('/login/')  
    return render(request, "register.html")
    
logger = logging.getLogger(__name__)

@csrf_exempt
def submit_rating(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            rating = data.get('rating')
            user = request.user  # Assuming the user is authenticated

            logger.debug(f'Received data: product_id={product_id}, rating={rating}, user={user}')

            if not user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'User not authenticated'}, status=403)

            product = Product.objects.get(id=product_id)
            # Check if the user has already rated this product
            product_rating, created = ProductRating.objects.get_or_create(
                product=product,
                user=user,
                defaults={'rating': rating}
            )
            if not created:
                # Update the rating if it already exists
                product_rating.rating = rating
                product_rating.save()

            return JsonResponse({'status': 'success'})
        except Product.DoesNotExist:
            logger.error(f'Product with id={product_id} does not exist.')
            return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)
        except Exception as e:
            logger.error(f'Error processing rating: {e}')
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def fpass(request):
    if request.method == 'POST':
        print("yess")
        email=request.POST.get("email")
        print("email:",email)
        user = Customer.objects.filter(email=email).first()
        if user:
            reset_code = ''.join(random.choices('0123456789', k=6))
            send_mail(
                'Password Reset Code',
                f'Your password reset code is: {reset_code}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            request.session['reset_code'] = reset_code
            request.session['reset_email'] = email
            return redirect('/entercode')
        else:
            return render(request, 'fpass.html', {'error_message': 'Email not found. Please enter a registered email.'})
    return render(request, 'fpass.html')

def entercode(request):
    if request.method == 'POST':
        entered_code = request.POST.get('code')
        stored_code = request.session.get('reset_code')
        if entered_code == stored_code:
            return redirect('/resetpass')
        else:
            messages.error(request, "Invalid code. Please enter the correct code.")
            return redirect('/entercode/')
    return render(request, 'entercode.html')


def resend_resetcode(request):
    email = request.session.get('reset_email')
    reset_code = ''.join(random.choices('0123456789', k=6))    
    send_mail(
        'Password Reset Code',
        f'Your new password reset code is: {reset_code}',
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )
    request.session['reset_code'] = reset_code
    return redirect('/entercode/')


def resetpass(request):
    if request.method == 'POST':
        new_password = request.POST.get('newpassword')
        # Get the email from session
        email = request.session.get('reset_email')
        user = Customer.objects.filter(email=email).first()
        if user:
            # Set the new password using Django's make_password function
            user.password = make_password(new_password)
            user.save()
            # Clear session variables
            del request.session['reset_code']
            del request.session['reset_email']
            return redirect('/login/')  # Redirect to login page after password reset
        else:
            # Handle case where email is not found
            messages.error(request, "Email not found. Please try again.")
            return render(request, 'resetpass.html')
    return render(request, 'resetpass.html')

@csrf_exempt
def review_submit(request):
    if request.method == 'POST':
        print("yess")
        review_comment = request.POST.get('review_comment')
        review = Review(comment=review_comment)
        review.save()
        return JsonResponse({'message': 'Review submitted successfully!'})
    return render('#')