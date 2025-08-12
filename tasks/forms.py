from django import forms
from django.utils import timezone
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Escribe una tarea...'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Descripción de la tarea...'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date'}),
            'priority': forms.Select(attrs={
                'class': 'form-control'}),
            'category': forms.Select(attrs={ 
                'class': 'form-control'
            }),
        }
        
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.localdate():
            raise forms.ValidationError("La fecha de vencimiento no puede ser anterior a hoy.")
        return due_date    
    
    def clean_title(self):
        t = (self.cleaned_data.get('title') or '').strip()
        if not t:
            raise forms.ValidationError("El título no puede estar vacío.")
        return t