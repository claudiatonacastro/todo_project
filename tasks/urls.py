from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('stats/', views.task_stats, name='task_stats'),
    path('combined/', views.combined_queries, name='combined_queries'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('complete/<int:task_id>/', views.complete_task, name='complete_task'),
    path('edit/<int:task_id>/', views.edit_task, name='edit_task'),
    # ⬇️ nuevas rutas para papelera
    path('trash/', views.trash_list, name='trash_list'),
    path('restore/<int:pk>/', views.task_restore, name='task_restore'),
    path('hard-delete/<int:pk>/', views.task_hard_delete, name='task_hard_delete'),
]