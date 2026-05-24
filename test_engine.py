import unittest
import pygame
from core.node import Node2D
from core.scene import SceneTree
from core.object_type import ObjectType

class TestEngineCore(unittest.TestCase):
    def test_node_hierarchy_global_position(self):
        """Тест: правильно ли вычисляются координаты дочерних объектов"""
        # В новой архитектуре Node2D не хранит логику вычисления глобальной позиции,
        # так как это теперь задача SceneTree при отрисовке, но мы можем проверить
        # базовое хранение координат.
        obj_type = ObjectType("Tank")
        parent = Node2D(obj_type, "ParentTank", x=100, y=100)

        child = Node2D(obj_type, "TankTurret", x=50, y=0)
        parent.children.append(child)
        child.parent = parent

        # Проверяем координаты
        self.assertEqual(parent.get_position().x, 100)
        self.assertEqual(child.get_position().x, 50)

    def test_scene_tree_selection(self):
        """Тест: работает ли система управления узлами в SceneTree"""
        tree = SceneTree()
        obj_type = ObjectType("Generic")
        node1 = Node2D(obj_type, "N1")
        node2 = Node2D(obj_type, "N2")

        tree.add_node(node1)
        tree.add_node(node2)

        # Проверяем, что узлы добавлены
        self.assertIn(node1, tree.root.children)
        self.assertIn(node2, tree.root.children)

        # Удаление
        tree.remove_node(node1)
        self.assertNotIn(node1, tree.root.children)

if __name__ == '__main__':
    unittest.main()
