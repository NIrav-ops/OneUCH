class NotificationMessage:

    @staticmethod
    def build(event):

        return {
            "title": event.name,
            "message": str(event.payload),
        }