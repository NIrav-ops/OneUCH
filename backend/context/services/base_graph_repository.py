from abc import ABC, abstractmethod


class BaseGraphRepository(ABC):
    """
    Enterprise Graph Repository Contract.

    Every graph backend (Django ORM, Neo4j, etc.)
    must implement this interface.
    """

    @abstractmethod
    def all_objects(self):
        pass

    @abstractmethod
    def object_count(self) -> int:
        pass

    @abstractmethod
    def relationship_count(self) -> int:
        pass

    @abstractmethod
    def neighbors(self, business_object):
        pass

    @abstractmethod
    def outgoing_relationships(self, business_object):
        pass

    @abstractmethod
    def incoming_relationships(self, business_object):
        pass

    @abstractmethod
    def graph_statistics(self):
        pass

    @abstractmethod
    def isolated_objects(self):
        pass