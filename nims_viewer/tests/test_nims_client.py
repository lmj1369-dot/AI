import httpx
import sys
from pathlib import Path

import pytest

from nims_viewer.client import NimsClient
from nims_viewer.config import resolve_env_path


@pytest.mark.asyncio
async def test_search_bssh_auth_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="AUTH_FAIL")

    transport = httpx.MockTransport(mock_handler)
    original_client = httpx.AsyncClient

    def mocked_client(**kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)

    client = NimsClient(api_key="BAD_KEY")
    with pytest.raises(ValueError, match="인증키가 잘못되었거나 권한이 없습니다"):
        await client.search_bssh(bizrno="1234567890")


@pytest.mark.asyncio
async def test_search_bssh_network_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed")

    transport = httpx.MockTransport(mock_handler)
    original_client = httpx.AsyncClient

    def mocked_client(**kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)

    client = NimsClient(api_key="GOOD_KEY")
    with pytest.raises(ValueError, match="인터넷 연결에 문제가 있거나 NIMS 서버에 연결할 수 없습니다"):
        await client.search_bssh(bizrno="1234567890")


@pytest.mark.asyncio
async def test_search_bssh_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    sample_json = {
        "RESULT_CODE": 0,
        "RESULT_MSG": "정상처리되었습니다.",
        "TOTAL_COUNT": 2,
        "IS_END_YN": "Y",
        "list": [
            {
                "BSSH_CD": "B00012345",
                "BSSH_NM": "동국온누리약국",
                "INDUTY_NM": "약국",
                "HDNT_CD": "01",
                "HDNT_NM": "약국",
                "BIZRNO": "1234567890",
                "RPRSNTV_NM": "홍길동",
                "CHRG_NM": "김담당",
                "HPTL_NO": "11100000",
                "JOIN_YN": "가입",
                "BSSH_STTUS_NM": "정상",
                "PRMISN_NO": "제1234호",
            },
            {
                "BSSH_CD": "B00099999",
                "BSSH_NM": "폐업약국",
                "INDUTY_NM": "약국",
                "HDNT_CD": "01",
                "HDNT_NM": "약국",
                "BIZRNO": "1234567890",
                "RPRSNTV_NM": "이순신",
                "CHRG_NM": "박담당",
                "HPTL_NO": "11100000",
                "JOIN_YN": "탈퇴",
                "BSSH_STTUS_NM": "폐업",
                "PRMISN_NO": "제5678호",
            },
        ],
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = str(request.url.query)
        captured["url"] = str(request.url)
        return httpx.Response(200, json=sample_json)

    transport = httpx.MockTransport(mock_handler)
    original_client = httpx.AsyncClient

    def mocked_client(**kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)

    client = NimsClient(api_key="TEST_API_KEY")
    result = await client.search_bssh(bizrno="123-45-67890", hptl_no="11100000")

    assert "k=TEST_API_KEY" in captured["query"]
    assert "bi=1234567890" in captured["query"]
    assert "hp=11100000" in captured["query"]
    assert "fg=1" in captured["query"]

    assert result["result_code"] == 0
    assert result["total_count"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["is_active_valid"] is True
    assert result["items"][1]["is_active_valid"] is False

    assert result["has_valid"] is True
    assert len(result["valid_bssh_list"]) == 1
    assert result["valid_bssh_list"][0]["bssh_cd"] == "B00012345"
    assert result["valid_bssh_list"][0]["bssh_nm"] == "동국온누리약국"


@pytest.mark.asyncio
async def test_search_bssh_xml_response(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <response>
        <RESULT_CODE>0</RESULT_CODE>
        <RESULT_MSG>정상</RESULT_MSG>
        <TOTAL_COUNT>1</TOTAL_COUNT>
        <IS_END_YN>Y</IS_END_YN>
        <list>
            <item>
                <BSSH_CD>B99887766</BSSH_CD>
                <BSSH_NM>동국종합병원</BSSH_NM>
                <INDUTY_NM>종합병원</INDUTY_NM>
                <HDNT_CD>02</HDNT_CD>
                <HDNT_NM>병원</HDNT_NM>
                <BIZRNO>2223344444</BIZRNO>
                <RPRSNTV_NM>강감찬</RPRSNTV_NM>
                <CHRG_NM>관리자</CHRG_NM>
                <HPTL_NO>33344455</HPTL_NO>
                <JOIN_YN>가입</JOIN_YN>
                <BSSH_STTUS_NM>정상</BSSH_STTUS_NM>
                <PRMISN_NO>허가999</PRMISN_NO>
            </item>
        </list>
    </response>
    """

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=sample_xml)

    transport = httpx.MockTransport(mock_handler)
    original_client = httpx.AsyncClient

    def mocked_client(**kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mocked_client)

    client = NimsClient(api_key="TEST_API_KEY")
    result = await client.search_bssh(bizrno="222-33-44444")

    assert result["result_code"] == 0
    assert len(result["items"]) == 1
    assert result["items"][0]["bssh_cd"] == "B99887766"
    assert result["items"][0]["is_active_valid"] is True
    assert result["valid_bssh_list"][0]["bssh_cd"] == "B99887766"
