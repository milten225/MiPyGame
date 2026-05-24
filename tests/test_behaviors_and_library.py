import unittest
import pygame
from core.object_type import ObjectType, ObjectKind
from core.node import Node2D
from core.scene import SceneTree
from core.behavior import BulletBehavior

class TestBehaviorsAndLibrary(unittest.TestCase):
    def test_behavior_execution(self):
        """Test that behaviors are correctly executed in simulation."""
        scene = SceneTree()
        ot = ObjectType("Bullet", ObjectKind.SPRITE)
        ot.behaviors.append(BulletBehavior(angle_degrees=0, speed=100))

        node = Node2D(ot, "B1", x=0, y=0)
        scene.add_node(node)

        scene.start_physics()
        self.assertTrue(scene.is_playing)

        # 1.0 second total
        scene.update(1.0)

        # BulletBehavior on_update moves instance.set_position(pos.x + dx, pos.y + dy)
        # dx = speed * dt = 100 * 1.0 = 100
        self.assertAlmostEqual(node.get_position().x, 100, delta=1)

    def test_camera_separation(self):
        """Test that editor and game cameras are separate."""
        scene = SceneTree()
        scene.camera_x = 500

        scene.start_physics()
        self.assertEqual(scene.game_camera_x, 0)
        self.assertEqual(scene.camera_x, 500)

        scene.game_camera_x = 100
        self.assertEqual(scene.camera_x, 500)

        scene.stop_physics()
        self.assertEqual(scene.camera_x, 500)

if __name__ == '__main__':
    unittest.main()
