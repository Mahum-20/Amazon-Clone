from django.db import models
import datetime
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

class AdminManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

class Admin(AbstractBaseUser):
    email = models.CharField(max_length=255, unique=True)
    objects = AdminManager()
    USERNAME_FIELD = 'email'
    password = models.CharField(max_length=255, null=True)
    class Meta:
        verbose_name_plural = 'Admins'
# Admin1.objects.create_user(email='nmahum217@gmail.com', password='1122')

# Create Customer Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    Firstname = models.CharField(max_length=20, blank=True)
    Lastame = models.CharField(max_length=200, blank=True)
    Username = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=200, blank=True)
    def __str__(self):
        return self.user.username

# Create a user Profile by default when user signs up
def create_profile(sender, instance, created, **kwargs):
	if created:
		user_profile = Profile(user=instance)
		user_profile.save()

# Automate the profile thing
post_save.connect(create_profile, sender=User)


# Categories of Products
class Category(models.Model):
	name = models.CharField(max_length=50)
	image = models.ImageField(upload_to='uploads/category/')
	def __str__(self):
		return self.name

	#@daverobb2011
	class Meta:
		verbose_name_plural = 'categories'


# Customers
class Customer(models.Model):
	username = models.CharField(max_length=50)
	email = models.EmailField(max_length=100)
	password = models.CharField(max_length=100)

	def __str__(self):
		return f'{self.username}'



# All of our Products
class Product(models.Model):
	name = models.CharField(max_length=500)
	price = models.DecimalField(default=0, decimal_places=2, max_digits=6)
	category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
	description = models.CharField(max_length=10000, default='', blank=True, null=True)
	image = models.ImageField(upload_to='uploads/product/')
	stock = models.IntegerField(default=0)

	def __str__(self):
		return self.name


# Customer Orders
class Order(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
	quantity = models.IntegerField(default=1)
	address = models.CharField(max_length=100, default='', blank=True)
	phone = models.CharField(max_length=20, default='', blank=True)
	date = models.DateField(default=datetime.datetime.today)
	status = models.BooleanField(default=False)

	def __str__(self):
		return self.product

class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField() 
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating for {self.product.name} by {self.user.username}"
    
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

