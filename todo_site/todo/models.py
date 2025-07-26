from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Todo(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    CATEGORY_CHOICES = [
        ('personal', 'Personal'),   
        ('work', 'Work'),
        ('shopping', 'Shopping'),
        ('health', 'Health'),
        ('education', 'Education'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='personal')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='todos')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    @property
    def is_overdue(self):
        if self.due_date and not self.completed:
            return timezone.now() > self.due_date
        return False

    @property
    def due_date_display(self):
        if not self.due_date:
            return ''
        
        now = timezone.now()
        diff = self.due_date - now
        
        if diff.days < 0:
            return f"Overdue by {abs(diff.days)} day(s)"
        elif diff.days == 0:
            return "Due today"
        elif diff.days == 1:
            return "Due tomorrow"
        else:
            return f"Due in {diff.days} day(s)"