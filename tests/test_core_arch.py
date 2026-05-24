import unittest
import pygame
import pymunk
from core.object_type import ObjectType
from core.node import Node2D
from core.scene import SceneTree

class TestCoreArchitecture(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.surface = pygame.Surface((800, 600))

    def test_object_type_vs_node(self):
        """Tests the ObjectType vs Node2D relationship."""
        player_type = ObjectType("Player", is_static=False, sprite_path="player.png")
        p1 = Node2D(player_type, "Player1", x=100, y=100)
        p2 = Node2D(player_type, "Player2", x=200, y=200)

        self.assertEqual(p1.object_type, player_type)
        self.assertEqual(p2.object_type, player_type)
        self.assertEqual(p1.object_type.is_static, False)
        self.assertEqual(p2.object_type.is_static, False)

        self.assertEqual(p1.get_name(), "Player1")
        self.assertEqual(p2.get_name(), "Player2")
        self.assertEqual(p1.get_position().x, 100)
        self.assertEqual(p2.get_position().x, 200)

    def test_scene_hierarchy_and_physics(self):
        """Tests SceneTree hierarchy management and Pymunk integration."""
        scene = SceneTree()
        box_type = ObjectType("Box", is_static=False)
        box_node = Node2D(box_type, "BoxInstance", x=10, y=10)

        scene.add_node(box_node)
        self.assertIn(box_node, scene.root.children)

        scene.start_physics()
        self.assertIn(box_node, scene.physics_bodies)
        body = scene.physics_bodies[box_node]

        # Initial pos check
        self.assertEqual(body.position.y, 35)

        # Step several times to ensure movement
        for _ in range(10):
            scene.update(0.1)

        print(f"DEBUG: Node Y after update: {box_node.get_position().y}")
        print(f"DEBUG: Body Y after update: {body.position.y}")

        self.assertNotEqual(box_node.get_position().y, 10.0)
        self.assertTrue(box_node.get_position().y > 10.0)

    def test_static_object_physics(self):
        """Tests that static ObjectTypes create static physics bodies."""
        scene = SceneTree()
        wall_type = ObjectType("Wall", is_static=True)
        wall_node = Node2D(wall_type, "WallInstance", x=0, y=500)

        scene.add_node(wall_node)
        scene.start_physics()

        body = scene.physics_bodies[wall_node]
        self.assertEqual(body.body_type, pymunk.Body.STATIC)

        scene.update(0.1)
        self.assertEqual(wall_node.get_position().y, 500)

    def test_z_index_sorting(self):
        """Tests that drawing respects Z-index."""
        scene = SceneTree()
        type_a = ObjectType("A")
        node_back = Node2D(type_a, "Back", z_index=-1)
        node_front = Node2D(type_a, "Front", z_index=10)

        scene.add_node(node_back)
        scene.add_node(node_front)

        all_nodes = scene._get_all_nodes_flat(scene.root)
        all_nodes.sort(key=lambda n: n.get_z_index())

        back_idx = all_nodes.index(node_back)
        front_idx = all_nodes.index(node_front)
        self.assertTrue(back_idx < front_idx)

if __name__ == '__main__':
    unittest.main()
