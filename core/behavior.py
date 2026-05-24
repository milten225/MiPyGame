import pygame
import math
from abc import ABC, abstractmethod

class BaseBehavior(ABC):
    """
    Abstract base class for all object behaviors.
    """
    def __init__(self):
        self.name = self.__class__.__name__

    def on_start(self, instance):
        """Called when the behavior starts (e.g., when the game begins)."""
        pass

    @abstractmethod
    def on_update(self, instance, dt, scene):
        """Called every frame during the game simulation."""
        pass

class PlatformerBehavior(BaseBehavior):
    """
    Standard platformer movement: left/right keys and jump.
    """
    def __init__(self):
        super().__init__()
        self.speed = 200
        self.jump_force = -400

    def on_update(self, instance, dt, scene):
        keys = pygame.key.get_pressed()
        pos = instance.get_position()

        dx = 0
        if keys[pygame.K_LEFT]: dx -= self.speed * dt
        if keys[pygame.K_RIGHT]: dx += self.speed * dt

        if instance in scene.physics_bodies:
            body = scene.physics_bodies[instance]
            v = body.velocity
            new_vx = (dx / dt) if dt > 0 else 0
            if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
                body.velocity = (new_vx, v.y)

            if keys[pygame.K_SPACE] and abs(v.y) < 1:
                body.apply_impulse_at_local_point((0, self.jump_force))
        else:
            instance.set_position(pos.x + dx, pos.y)

class BulletBehavior(BaseBehavior):
    """
    Constant movement in a fixed direction.
    """
    def __init__(self, angle_degrees=0, speed=400):
        super().__init__()
        self.speed = speed
        self.angle = angle_degrees

    def on_update(self, instance, dt, scene):
        rad = math.radians(self.angle)
        dx = math.cos(rad) * self.speed * dt
        dy = math.sin(rad) * self.speed * dt

        if instance in scene.physics_bodies:
            body = scene.physics_bodies[instance]
            body.velocity = (math.cos(rad) * self.speed, math.sin(rad) * self.speed)
        else:
            pos = instance.get_position()
            instance.set_position(pos.x + dx, pos.y + dy)

class TopDownMovement(BaseBehavior):
    """
    8-direction movement for RPGs or top-down shooters.
    """
    def __init__(self, speed=250):
        super().__init__()
        self.speed = speed

    def on_update(self, instance, dt, scene):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1

        if dx != 0 or dy != 0:
            mag = math.sqrt(dx*dx + dy*dy)
            dx, dy = (dx/mag) * self.speed, (dy/mag) * self.speed

            if instance in scene.physics_bodies:
                body = scene.physics_bodies[instance]
                body.velocity = (dx, dy)
            else:
                pos = instance.get_position()
                instance.set_position(pos.x + dx * dt, pos.y + dy * dt)
        elif instance in scene.physics_bodies:
            body = scene.physics_bodies[instance]
            body.velocity = (0, 0)
