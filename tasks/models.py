from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):  # soft delete masivo (queryset.delete())
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):  # borrado físico real
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        # Por defecto, solo registros NO eliminados
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('Alta', 'Alta'),
        ('Media', 'Media'),
        ('Baja', 'Baja'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateField(blank=True, null=True)
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='Media'
    )
    
    # Relación con categorías
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    # 👉 Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()                  # default: solo vivos
    all_objects = SoftDeleteQuerySet.as_manager()  # incluye vivos y borrados

    # Métodos
    def soft_delete(self):
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self):
        super().delete()
        
    def delete(self, using=None, keep_parents=False):
        # Si alguien llama obj.delete(), hacemos soft delete
        self.soft_delete()
            
    def __str__(self):
        return f"{self.title} - {self.priority} ({self.category.name if self.category else 'Sin categoría'})"
    