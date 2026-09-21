from rest_framework import viewsets


class UserScopedModelViewSet(viewsets.ModelViewSet):
    """Restricts every action to rows owned by the requesting user.

    `user` is always taken from the request, never from the payload, so a client
    cannot write into or read another account's data by passing an id.
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
