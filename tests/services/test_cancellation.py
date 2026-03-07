from quark_uploader.services.cancellation import UploadCancellationToken, UploadCancelled


def test_upload_cancellation_token_requests_stop():
    token = UploadCancellationToken()
    assert token.is_cancelled() is False
    token.request_stop()
    assert token.is_cancelled() is True


def test_upload_cancellation_token_raises_cancelled():
    token = UploadCancellationToken()
    token.request_stop()
    raised = False
    try:
        token.raise_if_cancelled()
    except UploadCancelled:
        raised = True
    assert raised is True
