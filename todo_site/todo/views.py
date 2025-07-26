from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from .models import Todo
from .forms import TodoForm


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('todo_list')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'todos/login.html')

from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

def register(request):
    if request.method == 'POST':
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        username = request.POST.get('email')  # Use actual username field
        email = request.POST.get('email')  # Use actual username field
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validation
        if not all([firstname, lastname, username, email, password, password_confirm]):
            messages.error(request, 'All fields are required')
            print('All fields are required')
            return redirect('register')

        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            print('Passwords do not match')
            return redirect('register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            print('Username already exists')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            print('Email already registered')
            return redirect('register')
        
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=firstname,
                last_name=lastname,
                email=email
            )
            user.save()
            login(request, user)  # Automatically log in after registration
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('todo_list')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')

    return render(request, 'todos/register.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

def privacy_policy(request):
    """
    Privacy policy view
    """
    return render(request, 'todos/privacy.html')
def terms_of_services(request):
    """"Terms of services view"""
    return render(request, 'todos/terms_of_service.html')


@login_required(login_url='login')
def todo_list(request):
    """
    Main todo list view with all CRUD operations, filtering, and searching
    """
    # Get user's todos only
    todos = Todo.objects.filter(user=request.user)
    
    # Handle POST requests (form submissions)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            # Add new todo
            form = TodoForm(request.POST)
            if form.is_valid():
                todo = form.save(commit=False)
                todo.user=request.user
                todo.save()
                messages.success(request, 'Task added successfully!')
                return redirect('todo_list')
            else:
                messages.error(request, 'Please correct the errors below.')
                
        elif action == 'toggle':
            # Toggle completion status
            completed = 'completed' in request.POST  # ✅ Bu True yoki False beradi
            todo_id = request.POST.get('todo_id')
            todo = get_object_or_404(Todo, id=todo_id)
            todo.completed = completed
            todo.save()
            status = "completed" if todo.completed else "pending"
            messages.success(request, f'Task marked as {status}!')
            
        elif action == 'delete':
            # Delete single todo
            todo_id = request.POST.get('todo_id')
            todo = get_object_or_404(Todo, id=todo_id,)
            todo_title = todo.title
            todo.user=request.user
            todo.delete()
            messages.success(request, f'Task "{todo_title}" deleted successfully!')
            
        elif action == 'mark_all_complete':
            # Mark all pending tasks as complete
            updated = todos.filter(completed=False).update(completed=True)
            messages.success(request, f'{updated} tasks marked as complete!')
            
        elif action == 'delete_completed':
            # Delete all completed tasks
            count = todos.filter(completed=True).count()
            todos.filter(completed=True).delete()
            messages.success(request, f'{count} completed tasks deleted!')
            
        elif action == 'delete_all':
            # Delete all tasks (with confirmation)
            count = todos.count()
            todos.delete()
            messages.success(request, f'All {count} tasks deleted!')
            
        return redirect('todo_list')
    
    else:
        form = TodoForm()
    
    # Apply search filter
    search = request.GET.get('search', '').strip()
    if search:
        todos = todos.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Apply status filter
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'completed':
        todos = todos.filter(completed=True)
    elif filter_type == 'pending':
        todos = todos.filter(completed=False)
    elif filter_type == 'overdue':
        todos = todos.filter(
            due_date__lt=timezone.now(), 
            completed=False
        )
    elif filter_type == 'today':
        today = timezone.now().date()
        todos = todos.filter(
            due_date__date=today,
            completed=False
        )
    elif filter_type == 'this_week':
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
        week_end = week_start + timedelta(days=6)
        todos = todos.filter(
            due_date__date__range=[week_start, week_end],
            completed=False
        )
    
    # Apply category filter
    category = request.GET.get('category')
    if category and category != 'all':
        todos = todos.filter(category=category)
        
    # Apply priority filter
    priority = request.GET.get('priority')
    if priority and priority != 'all':
        todos = todos.filter(priority=priority)
    
    # Apply sorting
    sort_by = request.GET.get('sort', 'created_desc')
    if sort_by == 'created_asc':
        todos = todos.order_by('created_at')
    elif sort_by == 'due_date':
        todos = todos.order_by('due_date', 'created_at')
    elif sort_by == 'priority':
        # Custom priority ordering: high=3, medium=2, low=1
        todos = todos.extra(
            select={
                'priority_order': "CASE WHEN priority='high' THEN 3 WHEN priority='medium' THEN 2 ELSE 1 END"
            }
        ).order_by('-priority_order', 'created_at')
    elif sort_by == 'title':
        todos = todos.order_by('title')
    elif sort_by == 'completed':
        todos = todos.order_by('completed', 'created_at')
    else:  # created_desc (default)
        todos = todos.order_by('-created_at')
    
    # Pagination
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [5, 10, 20, 50]:
            per_page = 10
    except ValueError:
        per_page = 10
        
    paginator = Paginator(todos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate comprehensive stats
    all_todos = Todo.objects.filter(user=request.user)
    now = timezone.now()
    today = now.date()
    
    stats = {
        'total': all_todos.count(),
        'completed': all_todos.filter(completed=True).count(),
        'pending': all_todos.filter(completed=False).count(),
        'overdue': all_todos.filter(
            due_date__lt=now, 
            completed=False
        ).count(),
        'due_today': all_todos.filter(
            due_date__date=today,
            completed=False
        ).count(),
        'high_priority': all_todos.filter(
            priority='high',
            completed=False
        ).count(),
        'completed_today': all_todos.filter(
            completed=True,
            updated_at__date=today
        ).count(),
    }
    
    # Calculate completion percentage
    if stats['total'] > 0:
        stats['completion_percentage'] = round(
            (stats['completed'] / stats['total']) * 100, 1
        )
    else:
        stats['completion_percentage'] = 0
    
    # Category breakdown
    category_stats = all_todos.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Priority breakdown
    priority_stats = all_todos.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')
    

    """ Progress stats matching your format """

    now = timezone.now()
    today = now.date()
    
    # Basic progress stats
    total_tasks = todos.count()
    completed_tasks = todos.filter(completed=True).count()
    
    # Calculate completion rate (67% format)
    completion_rate = f"{round((completed_tasks / total_tasks * 100))}%" if total_tasks > 0 else "0%"
    
    # Time-based progress  
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # This Week: 5 completed (format)
    completed_this_week = todos.filter(
        updated_at__date__gte=week_ago,
        completed=True
    ).count()
    
    # This Month: 18 completed (format)
    completed_this_month = todos.filter(
        updated_at__date__gte=month_ago,
        completed=True
    ).count()
    
    # Average/Day: 2.3 tasks (format)
    daily_avg = f"{round(completed_this_month / 30, 1)}" if completed_this_month > 0 else "0"
    
    # Simple progress data matching your format
    progress_data = {
        'completion_rate': completion_rate,  # "67%"
        'completed_this_week': completed_this_week,  # 5
        'completed_this_month': completed_this_month,  # 18  
        'daily_average': daily_avg,  # "2.3"
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
    }


    context = {
        'progress': progress_data,
        'form': form,
        'todos': page_obj,
        'stats': stats,
        'category_stats': category_stats,
        'priority_stats': priority_stats,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'current_filter': filter_type,
        'current_category': category,
        'current_priority': priority,
        'current_sort': sort_by,
        'search_query': search,
        'per_page': per_page,
    }
    
    return render(request, 'todos/todo_list.html', context)

@login_required(login_url='login')
def add_todo(request):
    """
    Dedicated view for adding new todos
    """
    if request.method == 'POST':
        form = TodoForm(request.POST)
        if form.is_valid():
            todo = form.save(commit=False)
            todo.user=request.user  
            todo.save()
            messages.success(request, f'Task "{todo.title}" added successfully!')
            
            # Redirect based on next parameter or default to list
            next_url = request.POST.get('next', 'todo_list')
            return redirect(next_url)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TodoForm()
    
    return redirect(todo_list)


@login_required(login_url='login')
def edit_todo(request, pk):
    """
    Edit existing todo
    """
    todo = get_object_or_404(Todo, id=pk)
        
    if request.method == 'POST':
        form = TodoForm(request.POST, instance=todo)
        completed = 'completed' in request.POST  # ✅ Bu True yoki False beradi
        todo.completed = completed
        todo.save()
        if form.is_valid():
            form.save()
            messages.success(request, f'Task "{todo.title}" updated successfully!')
            return redirect('todo_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TodoForm(instance=todo)
    
    context = {
        'form': form,
        'todo': todo,
        'page_title': f'Edit: {todo.title}',
    }
    return render(request, 'todos/edit_todo.html', context)


@login_required(login_url='login')
def delete_todo(request, pk):
    """
    Delete todo with confirmation
    """
    todo = Todo.objects.filter(user=request.user).get(id=pk)
    
    if request.method == 'POST':
        todo_title = todo.title
        todo.delete()
        messages.success(request, f'Task "{todo_title}" deleted successfully!')
        return redirect('todo_list')
    
    return redirect('todo_list')
# @login_required(login_url='login')
# def toggle_todo(request, todo_id):
#     """
#     Toggle todo completion status via AJAX or form
#     """
#     todo = get_object_or_404(Todo, id=todo_id,)
    
#     if request.method == 'POST':
#         todo.completed = not todo.completed
#         todo.save()
        
#         status = "completed" if todo.completed else "pending"
#         message = f'Task "{todo.title}" marked as {status}!'
        
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'success': True,
#                 'completed': todo.completed,
#                 'message': message
#             })
#         else:
#             messages.success(request, message)
#             return redirect('todo_list')
    
#     return redirect('todo_list')


# @login_required(login_url='login')
# def bulk_actions(request):
#     """
#     Handle bulk actions on todos
#     """
#     if request.method == 'POST':
#         action = request.POST.get('action')
#         selected_ids = request.POST.getlist('selected_todos')
        
#         if not selected_ids:
#             messages.error(request, 'No tasks selected.')
#             return redirect('todo_list')
        
#         # Ensure user owns all selected todos
#         todos = Todo.objects.filter(
#             id__in=selected_ids, 
           
#         )
        
#         if todos.count() != len(selected_ids):
#             messages.error(request, 'Invalid task selection.')
#             return redirect('todo_list')
        
#         if action == 'mark_complete':
#             updated = todos.filter(completed=False).update(completed=True)
#             messages.success(request, f'{updated} tasks marked as complete!')
            
#         elif action == 'mark_pending':
#             updated = todos.filter(completed=True).update(completed=False)
#             messages.success(request, f'{updated} tasks marked as pending!')
            
#         elif action == 'delete':
#             count = todos.count()
#             todos.delete()
#             messages.success(request, f'{count} tasks deleted!')
            
#         elif action == 'change_priority':
#             new_priority = request.POST.get('priority')
#             if new_priority in ['low', 'medium', 'high']:
#                 todos.update(priority=new_priority)
#                 messages.success(request, f'Priority updated for {todos.count()} tasks!')
#             else:
#                 messages.error(request, 'Invalid priority selected.')
                
#         elif action == 'change_category':
#             new_category = request.POST.get('category')
#             valid_categories = ['personal', 'work', 'shopping', 'health', 'education']
#             if new_category in valid_categories:
#                 todos.update(category=new_category)
#                 messages.success(request, f'Category updated for {todos.count()} tasks!')
#             else:
#                 messages.error(request, 'Invalid category selected.')
    
#     return redirect('todo_list')


# @login_required(login_url='login')
# def todo_stats(request):
#     """
#     Detailed statistics page
#     """
#     todos = Todo.objects.filter(user=request.user)
#     now = timezone.now()
    
#     # Basic stats
#     total = todos.count()
#     completed = todos.filter(completed=True).count()
#     pending = todos.filter(completed=False).count()
    
#     # Time-based stats
#     today = now.date()
#     week_ago = today - timedelta(days=7)
#     month_ago = today - timedelta(days=30)
    
#     stats = {
#         'total': total,
#         'completed': completed,
#         'pending': pending,
#         'completion_rate': round((completed / total * 100), 1) if total > 0 else 0,
#         'overdue': todos.filter(due_date__lt=now, completed=False).count(),
#         'due_today': todos.filter(due_date__date=today, completed=False).count(),
#         'completed_today': todos.filter(updated_at__date=today, completed=True).count(),
#         'completed_this_week': todos.filter(
#             updated_at__date__gte=week_ago, 
#             completed=True
#         ).count(),
#         'completed_this_month': todos.filter(
#             updated_at__date__gte=month_ago, 
#             completed=True
#         ).count(),
#         'created_this_week': todos.filter(created_at__date__gte=week_ago).count(),
#         'created_this_month': todos.filter(created_at__date__gte=month_ago).count(),
#     }
    
#     # Category breakdown
#     category_stats = todos.values('category').annotate(
#         total=Count('id'),
#         completed=Count('id', filter=Q(completed=True)),
#         pending=Count('id', filter=Q(completed=False))
#     ).order_by('-total')
    
#     # Priority breakdown
#     priority_stats = todos.values('priority').annotate(
#         total=Count('id'),
#         completed=Count('id', filter=Q(completed=True)),
#         pending=Count('id', filter=Q(completed=False))
#     ).order_by('-total')
    
#     # Recent activity (last 7 days)
#     recent_activity = []
#     for i in range(7):
#         date = today - timedelta(days=i)
#         created = todos.filter(created_at__date=date).count()
#         completed = todos.filter(updated_at__date=date, completed=True).count()
#         recent_activity.append({
#             'date': date,
#             'created': created,
#             'completed': completed
#         })
    
#     context = {
#         'stats': stats,
#         'category_stats': category_stats,
#         'priority_stats': priority_stats,
#         'recent_activity': recent_activity,
#         'page_title': 'Task Statistics'
#     }
    
#     return render(request, 'todos/stats.html', context)


# @login_required(login_url='login')
# def export_todos(request):
#     """
#     Export todos to CSV format
#     """
#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = f'attachment; filename="todos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
#     writer = csv.writer(response)
#     writer.writerow([
#         'Title', 'Description', 'Category', 'Priority', 
#         'Completed', 'Due Date', 'Created', 'Updated'
#     ])
    
#     todos = Todo.objects.order_by('-created_at')
    
#     for todo in todos:
#         writer.writerow([
#             todo.title,
#             todo.description,
#             todo.get_category_display(),
#             todo.get_priority_display(),
#             'Yes' if todo.completed else 'No',
#             todo.due_date.strftime('%Y-%m-%d %H:%M') if todo.due_date else '',
#             todo.created_at.strftime('%Y-%m-%d %H:%M'),
#             todo.updated_at.strftime('%Y-%m-%d %H:%M'),
#         ])
    
#     return response


# @login_required(login_url='login')
# def import_todos(request):
#     """
#     Import todos from CSV file
#     """
#     if request.method == 'POST' and request.FILES.get('csv_file'):
#         csv_file = request.FILES['csv_file']
        
#         if not csv_file.name.endswith('.csv'):
#             messages.error(request, 'Please upload a CSV file.')
#             return redirect('todo_list')
        
#         try:
#             # Read and decode CSV
#             decoded_file = csv_file.read().decode('utf-8').splitlines()
#             reader = csv.DictReader(decoded_file)
            
#             imported_count = 0
#             for row in reader:
#                 try:
#                     # Parse due date
#                     due_date = None
#                     if row.get('Due Date'):
#                         due_date = datetime.strptime(
#                             row['Due Date'], 
#                             '%Y-%m-%d %H:%M'
#                         )
                    
#                     # Create todo
#                     Todo.objects.create(
#                         title=row['Title'][:200],  # Truncate if too long
#                         description=row.get('Description', ''),
#                         category=row.get('Category', 'personal').lower(),
#                         priority=row.get('Priority', 'medium').lower(),
#                         completed=row.get('Completed', '').lower() in ['yes', 'true', '1'],
#                         due_date=due_date,
#                     )
#                     imported_count += 1
                    
#                 except Exception as e:
#                     # Skip invalid rows
#                     continue
            
#             messages.success(request, f'Successfully imported {imported_count} tasks!')
            
#         except Exception as e:
#             messages.error(request, f'Error importing file: {str(e)}')
    
#     return redirect('todo_list')


# @login_required(login_url='login')
# def search_todos(request):
#     """
#     AJAX search endpoint for live search
#     """
#     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         query = request.GET.get('q', '').strip()
        
#         if len(query) >= 2:  # Minimum 2 characters
#             todos = Todo.objects.filter(
#                 Q(title__icontains=query) | 
#                 Q(description__icontains=query)
#             )[:10]  # Limit results
            
#             results = []
#             for todo in todos:
#                 results.append({
#                     'id': todo.id,
#                     'title': todo.title,
#                     'description': todo.description[:100] + '...' if len(todo.description) > 100 else todo.description,
#                     'category': todo.category,
#                     'priority': todo.priority,
#                     'completed': todo.completed,
#                     'due_date': todo.due_date.isoformat() if todo.due_date else None,
#                 })
            
#             return JsonResponse({'results': results})
    
#     return JsonResponse({'results': []})


# @login_required(login_url='login')
# def clear_completed(request):
#     """
#     Clear all completed todos
#     """
#     if request.method == 'POST':
#         count = Todo.objects.filter(
#             completed=True
#         ).count()
        
#         Todo.objects.filter(
#             completed=True
#         ).delete()
        
#         messages.success(request, f'{count} completed tasks cleared!')
    
#     return redirect('todo_list')


# def todo_detail(request, todo_id):
#     """
#     Detailed view of a single todo
#     """
#     todo = get_object_or_404(Todo, id=todo_id,)
    
#     context = {
#         'todo': todo,
#         'page_title': todo.title,
#     }
    
#     return render(request, 'todos/todo_detail.html', context)