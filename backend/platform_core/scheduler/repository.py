class ScheduleRepository:

    _schedules = []

    @classmethod
    def save(cls, schedule):

        cls._schedules.append(schedule)

    @classmethod
    def all(cls):

        return list(cls._schedules)

    @classmethod
    def clear(cls):

        cls._schedules.clear()

    @classmethod
    def count(cls):

        return len(cls._schedules)