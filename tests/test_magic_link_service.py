from magic_link_service import Asset, DeliveryJob, SignInRequest, build_creator_delivery


def test_creator_delivery_requires_processing_before_delivery() -> None:
    job = build_creator_delivery(Asset("asset-42", "Spring lookbook", "creator@example.com"))

    assert job.state == "queued"
    assert job.process() == "processed"
    assert job.deliver() == "delivered"
    assert job.events == ["asset processed", "creator delivery prepared"]


def test_sign_in_request_keeps_checkout_return_path() -> None:
    request = SignInRequest("buyer@example.com", "user-7", "/checkout/review")

    assert request.email == "buyer@example.com"
    assert request.return_to == "/checkout/review"
