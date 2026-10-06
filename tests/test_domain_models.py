import unittest

from cinecue.domain import (
    ContentItem,
    ContentType,
    RecommendationItem,
    RecommendationResult,
    UserRequest,
    WatchOffer,
)


class ContentItemTests(unittest.TestCase):
    def test_movie_and_tv_share_the_same_model(self) -> None:
        movie = ContentItem(
            content_id="movie_Q100",
            content_type=ContentType.MOVIE,
            title="Example Movie",
            runtime_minutes=110,
        )
        tv = ContentItem(
            content_id="tv_Q200",
            content_type=ContentType.TV,
            title="Example Series",
            episode_runtime_minutes=45,
        )

        self.assertEqual(movie.content_type, ContentType.MOVIE)
        self.assertEqual(tv.content_type, ContentType.TV)

    def test_rejects_empty_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "title must not be empty"):
            ContentItem(
                content_id="movie_Q100",
                content_type=ContentType.MOVIE,
                title="  ",
            )

    def test_rejects_vote_average_outside_supported_scale(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 0 and 10"):
            ContentItem(
                content_id="movie_Q100",
                content_type=ContentType.MOVIE,
                title="Example Movie",
                vote_average=10.1,
            )


class UserRequestTests(unittest.TestCase):
    def test_rejects_non_positive_max_runtime(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            UserRequest(raw_query="A short romance", max_runtime_minutes=0)


class RecommendationResultTests(unittest.TestCase):
    def test_keeps_score_and_reasons_with_each_content_item(self) -> None:
        content = ContentItem(
            content_id="movie_Q100",
            content_type=ContentType.MOVIE,
            title="Example Movie",
            watch_offers=(
                WatchOffer(
                    region="CH",
                    provider_name="Example Provider",
                ),
            ),
        )
        request = UserRequest(raw_query="A light romance")
        recommendation = RecommendationItem(
            content=content,
            score=0.8,
            reasons=("Matches the requested tone",),
        )

        result = RecommendationResult(
            request=request,
            recommendations=(recommendation,),
        )

        self.assertEqual(result.recommendations[0].content, content)
        self.assertEqual(result.recommendations[0].score, 0.8)
        self.assertEqual(
            result.recommendations[0].reasons,
            ("Matches the requested tone",),
        )


if __name__ == "__main__":
    unittest.main()
