import unittest
import pygame
from core.node import Node2D
from core.scene import SceneTree

class TestEngineCore(unittest.TestCase):
    def test_node_hierarchy_global_position(self):
        """Тест: правильно ли вычисляются координаты дочерних объектов"""
        parent = Node2D("ParentTank")
        parent.position.update(100, 100) # Танк на координатах 100, 100

        child = Node2D("TankTurret")
        child.position.update(50, 0)     # Башня смещена на 50 пикселей вправо
        parent.add_child(child)

        # Проверяем локальные координаты башни
        self.assertEqual(child.position.x, 50)

        # Проверяем глобальные координаты башни (должно быть 100 + 50 = 150)
        global_pos = child.get_global_position()
        self.assertEqual(global_pos.x, 150)
        self.assertEqual(global_pos.y, 100)

    def test_scene_tree_selection(self):
        """Тест: работает ли система снятия выделения с объектов (Gizmo)"""
        tree = SceneTree()
        node1 = Node2D("N1")
        node2 = Node2D("N2")
        tree.root.add_child(node1)
        tree.root.add_child(node2)

        node1.selected = True
        node2.selected = True

        # Снимаем выделение со всей сцены
        tree.clear_selection()

        # Проверяем, что флаги сброшены
        self.assertFalse(node1.selected)
        self.assertFalse(node2.selected)

if __name__ == '__main__':
    unittest.main()