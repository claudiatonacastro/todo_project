from django.shortcuts import render, redirect, get_object_or_404
from .models import Task, Category
from .forms import TaskForm 
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date
from django.db import IntegrityError, DatabaseError

def task_list(request):
    default_categories = [
        ("Trabajo", "Tareas relacionadas con el trabajo"),
        ("Personal", "Tareas personales y domésticas"),
        ("Estudio", "Tareas relacionadas con estudios"),
        ("Otro", "Tareas relacionadas con otras cosas"),
    ]
    for name, desc in default_categories:
        Category.objects.get_or_create(name=name, defaults={"description": desc})

    # Query base
    tasks = Task.objects.select_related('category').all().order_by('due_date', 'priority')

    # Filtro por estado
    status = request.GET.get('status', 'all')
    if status == 'pending':
        tasks = tasks.filter(completed=False)
    elif status == 'completed':
        tasks = tasks.filter(completed=True)

    # Filtro por categoría (?category=<id>)
    category_id = request.GET.get('category')
    if category_id and category_id.isdigit():
        tasks = tasks.filter(category_id=category_id)

    # Form (vinculado si POST para conservar valores)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            try:
                form.save() 
                return redirect('task_list')
            except (IntegrityError, DatabaseError) as e:
                msg = str(e)

                # Mapea el mensaje del trigger a errores de campos del form
                if 'vencimiento' in msg or 'fecha' in msg:
                    form.add_error('due_date', 'La fecha no puede ser anterior a hoy (validado por la base de datos).')
                elif 'Prioridad inválida' in msg:
                    form.add_error('priority', 'Prioridad inválida. Debe ser Alta, Media o Baja.')
                elif 'título' in msg or 'titulo' in msg:
                    form.add_error('title', 'El título no puede estar vacío.')
                else:
                    # Error general por si cambia el texto del trigger
                    form.add_error(None, 'No se pudo guardar por una restricción en la base de datos.')
        # si no es válido, cae al render y se muestran errores del form
    else:
        form = TaskForm()

    categories = Category.objects.order_by('name')

    return render(
        request,
        'tasks/task_list.html',
        {
            'tasks': tasks,
            'form': form,
            'categories': categories,
            'selected_category': category_id,
            'status': status
        }
    )

def delete_task(request, task_id):
    # ahora SOFT delete
    task = get_object_or_404(Task.all_objects, pk=task_id)  # acepta vivos y borrados
    task.soft_delete()
    return redirect('task_list')

def complete_task(request, task_id):
    task = Task.objects.get(id=task_id)
    task.completed = True
    task.save()
    return redirect('task_list')

def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)

    return render(
        request, 
        'tasks/edit_task.html', {
            'form': form, 
            'task': task
    })

def task_stats(request):
    hoy = timezone.localdate()

    # Consultas de agrupaciones
    tasks_por_categoria = (
        Task.objects
        .values('category__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    estado_por_prioridad = (
        Task.objects
        .values('priority')
        .annotate(
            pendientes=Count('id', filter=Q(completed=False)),
            completadas=Count('id', filter=Q(completed=True)),
        )
        .order_by('priority')
    )

    vencidas_por_categoria = (
        Task.objects
        .values('category__name')
        .annotate(vencidas=Count('id', filter=Q(completed=False, due_date__lt=hoy)))
        .order_by('-vencidas')
    )

    por_dia = (
        Task.objects
        .values('due_date')
        .annotate(total=Count('id'))
        .order_by('due_date')
    )

    context = {
        'tasks_por_categoria': tasks_por_categoria,
        'estado_por_prioridad': estado_por_prioridad,
        'por_dia': por_dia,
        # 👉 NUEVO:
        'vencidas_por_categoria': vencidas_por_categoria,  # por si quieres listarlo también

        # >>> Datos para Chart.js
        'cat_labels': [r['category__name'] or 'Sin categoría' for r in tasks_por_categoria],
        'cat_totals': [r['total'] for r in tasks_por_categoria],

        'prior_labels': [r['priority'] for r in estado_por_prioridad],
        'prior_pendientes': [r['pendientes'] for r in estado_por_prioridad],
        'prior_completadas': [r['completadas'] for r in estado_por_prioridad],

        'dia_labels': [r['due_date'].isoformat() if r['due_date'] else 'Sin fecha' for r in por_dia],
        'dia_totals': [r['total'] for r in por_dia],
        
        # 👉 NUEVO: datos para la gráfica de vencidas por categoría
        'venc_labels': [r['category__name'] or 'Sin categoría' for r in vencidas_por_categoria],
        'venc_totals': [r['vencidas'] for r in vencidas_por_categoria],
    }
    
    return render(request, 'tasks/task_stats.html', context)

def combined_queries(request):
    sday = request.GET.get('day') 
    op = request.GET.get('op', 'union')            # union | intersection | difference
    prio = request.GET.get('prio', 'Alta')         # Alta | Media | Baja

    #Fecha Q1 (si no viene o es inválida, usa hoy)
    try:
        q1_day = date.fromisoformat(sday) if sday else timezone.localdate()
    except ValueError:
        q1_day = timezone.localdate()

    # ¡IMPORTANTE! Las columnas de ambos querysets deben ser las mismas
    cols = ('id', 'title', 'due_date', 'priority', 'category__name',
            'category__name', 'completed', 'description')

    q1 = Task.objects.filter(due_date=q1_day).values(*cols)
    q2 = Task.objects.filter(priority=prio).values(*cols)

    if op == 'intersection':
        result = q1.intersection(q2)
        op_label = "Intersección (HOY ∩ prioridad seleccionada)"
    elif op == 'difference':
        result = q1.difference(q2)
        op_label = "Diferencia (HOY − prioridad seleccionada)"
    else:
        result = q1.union(q2)
        op = 'union'  # normaliza
        op_label = "Unión (HOY ∪ prioridad seleccionada)"

    result = result.order_by('title')  # ordenar por una columna presente en values()

    context = {
        'prio': prio,
        'op': op,
        'op_label': op_label,
        'items': list(result),  # opcional convertir a lista para evitar re-evaluación
        'q1_day': q1_day,                 # para mostrar
        'q1_day_str': q1_day.isoformat(), # para value del <input type="date">
    }
    return render(request, 'tasks/combined_task.html', context)

def trash_list(request):
    tasks = Task.all_objects.dead().select_related('category').order_by('-deleted_at')
    return render(request, 'tasks/trash_list.html', {'tasks': tasks})

def task_restore(request, pk):
    task = get_object_or_404(Task.all_objects, pk=pk)  # puede estar borrada
    task.restore()
    return redirect('trash_list')

def task_hard_delete(request, pk):
    task = get_object_or_404(Task.all_objects, pk=pk)
    task.hard_delete()
    return redirect('trash_list')