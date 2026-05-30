from app.annotation.detection.review_cache import ReviewCacheMixin
from app.annotation.detection.review_annotations import ReviewAnnotationsMixin
from app.annotation.detection.review_navigation import ReviewNavigationMixin


class ReviewNavMixin(ReviewCacheMixin, ReviewAnnotationsMixin, ReviewNavigationMixin):
    """Composes review cache, annotation rebuild, and navigation into a single mixin."""
    pass
