from collections import deque
from typing import List
from context.models import BusinessObject
from context.services.graph_repository import GraphRepository
from context.constants import (
    DEFAULT_MAX_DEPTH,
)
from context.constants import (
    DEFAULT_SHORTEST_PATH_DEPTH,
)

from context.exceptions import (
    GraphTraversalError,
    BusinessObjectNotFound,
)


class GraphTraversalService:
    """
    Enterprise Graph Traversal Service.

    Current:
        Breadth First Search (BFS)

    Future:
        DFS
        Shortest Path
        Graph Ranking
        AI Traversal
    """

    def __init__(self):

        self.repository = GraphRepository()

    def bfs(
        self,
        *,
        start_object,
        max_depth=DEFAULT_MAX_DEPTH,
        ) -> List[BusinessObject]:
        """
        Breadth First Search.

        Returns every reachable BusinessObject
        up to max_depth.
        """

        if start_object is None:
            return []

        visited = set()

        queue = deque()

        queue.append(
            (
                start_object,
                0,
            )
        )

        results = []

        while queue:

            current, depth = queue.popleft()

            if current.id in visited:
                continue

            visited.add(
                current.id
            )

            results.append(current)

            if depth >= max_depth:
                continue

            neighbours = self.repository.neighbors(
                current
            )

            for neighbour in neighbours:

                if neighbour.id not in visited:

                    queue.append(
                        (
                            neighbour,
                            depth + 1,
                        )
                    )
        return list(results)        

    def dfs(
        self,
        *,
        start_object,
        max_depth=DEFAULT_MAX_DEPTH,
        ) -> List[BusinessObject]:
        """
        Depth First Search.
        """

        if start_object is None:
            return []

        visited = set()
        results = []

        def traverse(node, depth):

            if node.id in visited:
                return

            visited.add(node.id)
            results.append(node)

            if depth >= max_depth:
                return

            neighbours = self.repository.neighbors(node)

            for neighbour in neighbours:
                traverse(
                    neighbour,
                    depth + 1,
                )

        traverse(
            start_object,
            0,
        )

        return list(results)      

    def path_exists(
        self,
        *,
        start_object,
        target_object,
        max_depth=DEFAULT_SHORTEST_PATH_DEPTH,
    ) -> bool:
        """
        Returns True if a path exists between two BusinessObjects.
        """

        if start_object is None or target_object is None:
            return False

        if start_object == target_object:
            return True

        visited = set()

        queue = deque()

        queue.append(
            (
                start_object,
                0,
            )
        )

        while queue:

            current, depth = queue.popleft()

            if current.id in visited:
                continue

            visited.add(current.id)

            if current == target_object:
                return True

            if depth >= max_depth:
                continue

            neighbours = self.repository.neighbors(current)

            for neighbour in neighbours:

                if neighbour.id not in visited:

                    queue.append(
                        (
                            neighbour,
                            depth + 1,
                        )
                    )

        return False      
    def shortest_path(
        self,
        *,
        start_object,
        target_object,
        max_depth=DEFAULT_SHORTEST_PATH_DEPTH,
    ) -> List[BusinessObject]:
        """
        Returns the shortest path between two BusinessObjects.

        Returns:

            []

            if no path exists.
        """

        if start_object is None or target_object is None:
            return []

        if start_object == target_object:
            return [start_object]

        visited = set()

        queue = deque()

        queue.append(
            (
                start_object,
                [start_object],
                0,
            )
        )

        while queue:

            current, path, depth = queue.popleft()

            if current.id in visited:
                continue

            visited.add(current.id)

            if current == target_object:
                return list(path)

            if depth >= max_depth:
                continue

            neighbours = self.repository.neighbors(
                current
            )

            for neighbour in neighbours:

                if neighbour.id not in visited:

                    queue.append(
                        (
                            neighbour,
                            path + [neighbour],
                            depth + 1,
                        )
                    )

        return []
    
    def distance(
        self,
        *,
        start_object,
        target_object,
        max_depth=DEFAULT_SHORTEST_PATH_DEPTH,
    ) -> int:
        """
        Returns the minimum hop count.

        Returns

        -1

        if unreachable.
        """

        path = self.shortest_path(

            start_object=start_object,

            target_object=target_object,

            max_depth=max_depth,

        )

        if not path:

            return -1

        return len(path) - 1
    def reachable_objects(
        self,
        *,
        start_object,
        max_depth=DEFAULT_MAX_DEPTH,
    ) -> List[BusinessObject]:
        """
        Returns every reachable object
        excluding the starting node.
        """

        results = self.bfs(

            start_object=start_object,

            max_depth=max_depth,

        )

        if not results:

            return []

        return list(results[1:])
