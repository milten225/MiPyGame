import unittest
import pygame
from core.object_type import ObjectType, ObjectKind
from core.node import Node2D
from core.scene import SceneTree
from core.behavior import BulletBehavior

class TestFinalArch(unittest.TestCase):
    def test_hierarchy_global_pos(self):
        """Test that global positions account for hierarchy."""
        ot = ObjectType("T")
        p = Node2D(ot, "Parent", x=100, y=100)
        c = Node2D(ot, "Child", x=50, y=50)
        c.parent = p
        p.children.append(c)

        self.assertEqual(c.get_global_position().x, 150)
        self.assertEqual(c.get_global_position().y, 150)

    def test_resource_caching(self):
        """Test that ObjectType caches its render surface."""
        ot = ObjectType("Sprite", width=10, height=10)
        surf1 = ot.get_render_surface()
        surf2 = ot.get_render_surface()
        self.assertIs(surf1, surf2)

        ot.width = 20
        surf3 = ot.get_render_surface()
        self.assertIsNot(surf1, surf3)

    def test_recursive_removal(self):
        """Test that removing a node also cleans up its children."""
        scene = SceneTree()
        ot = ObjectType("T")
        p = Node2D(ot, "P")
        c = Node2D(ot, "C")
        scene.add_node(p)
        scene.add_node(c, parent=p)

        self.assertIn(c, p.children)
        scene.remove_node(p)
        self.assertNotIn(p, scene.node_state)
        self.assertNotIn(c, scene.node_state)

if __name__ == '__main__':
    unittest.main()
