import json
import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NimsApiError(Exception):
    def __init__(self, code: int | str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"NIMS API 오류 [{code}]: {message}")


class NimsClient:
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://www.nims.or.kr/api/bsshinfo_st_v1.do",
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key.strip()
        self.api_url = api_url.strip()
        self.timeout = timeout

    def _raise_for_response(self, response: httpx.Response) -> None:
        status = response.status_code
        if status == 401:
            raise ValueError("인증키가 잘못되었거나 권한이 없습니다. NIMS API 인증키를 다시 확인해주세요.")
        if status == 403:
            raise ValueError("NIMS API 접근이 거부되었습니다. 인증키 권한 또는 서버 허용 범위를 확인해주세요.")
        if status in (404, 405):
            raise ValueError("NIMS API 주소가 올바르지 않습니다. 관리자에게 문의해주세요.")
        if status >= 500:
            raise ValueError("NIMS 서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        if status >= 400:
            raise ValueError(f"NIMS API 요청이 거부되었습니다. (HTTP {status})")

    async def search_bssh(
        self,
        *,
        bizrno: str | None = None,
        hptl_no: str | None = None,
        bssh_nm: str | None = None,
        bssh_cd: str | None = None,
        page: int = 1,
        range_fg: str = "1",
        range_fg2: str = "1",
        ymd: str | None = None,
        api_key_override: str | None = None,
    ) -> dict[str, Any]:
        key = (api_key_override or self.api_key).strip()
        if not key:
            raise ValueError("NIMS API 인증키(K)가 설정되지 않았습니다.")

        clean_bizrno = (bizrno or "").replace("-", "").strip()
        clean_hptl_no = (hptl_no or "").strip()
        clean_bssh_nm = (bssh_nm or "").strip()
        clean_bssh_cd = (bssh_cd or "").strip()
        clean_ymd = (ymd or "").replace("-", "").strip()

        query_params: dict[str, str] = {
            "k": key,
            "K": key,
            "fg": range_fg.strip() or "1",
            "pg": str(page),
            "fg2": range_fg2.strip() or "1",
            "bi": clean_bizrno,
            "hp": clean_hptl_no,
            "bn": clean_bssh_nm,
            "bc": clean_bssh_cd,
            "ymd": clean_ymd,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.api_url, params=query_params)
                self._raise_for_response(response)
                raw_text = response.text
        except httpx.ConnectError as err:
            raise ValueError("인터넷 연결에 문제가 있거나 NIMS 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.") from err
        except httpx.TimeoutException as err:
            raise ValueError("NIMS 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.") from err
        except httpx.HTTPError as err:
            raise ValueError("NIMS API 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") from err

        parsed = self._parse_response(raw_text)
        return self._normalize_result(parsed)

    def search_bssh_sync(
        self,
        *,
        bizrno: str | None = None,
        hptl_no: str | None = None,
        bssh_nm: str | None = None,
        bssh_cd: str | None = None,
        page: int = 1,
        range_fg: str = "1",
        range_fg2: str = "1",
        ymd: str | None = None,
        api_key_override: str | None = None,
    ) -> dict[str, Any]:
        key = (api_key_override or self.api_key).strip()
        if not key:
            raise ValueError("NIMS API 인증키(K)가 설정되지 않았습니다.")

        clean_bizrno = (bizrno or "").replace("-", "").strip()
        clean_hptl_no = (hptl_no or "").strip()
        clean_bssh_nm = (bssh_nm or "").strip()
        clean_bssh_cd = (bssh_cd or "").strip()
        clean_ymd = (ymd or "").replace("-", "").strip()

        query_params: dict[str, str] = {
            "k": key,
            "K": key,
            "fg": range_fg.strip() or "1",
            "pg": str(page),
            "fg2": range_fg2.strip() or "1",
            "bi": clean_bizrno,
            "hp": clean_hptl_no,
            "bn": clean_bssh_nm,
            "bc": clean_bssh_cd,
            "ymd": clean_ymd,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, params=query_params)
                self._raise_for_response(response)
                raw_text = response.text
        except httpx.ConnectError as err:
            raise ValueError("인터넷 연결에 문제가 있거나 NIMS 서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요.") from err
        except httpx.TimeoutException as err:
            raise ValueError("NIMS 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.") from err
        except httpx.HTTPError as err:
            raise ValueError("NIMS API 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.") from err

        parsed = self._parse_response(raw_text)
        return self._normalize_result(parsed)

    def _parse_response(self, raw_text: str) -> dict[str, Any]:
        raw_clean = raw_text.strip()
        # 1. JSON 시도
        try:
            return json.loads(raw_clean)
        except json.JSONDecodeError:
            pass

        # 2. XML 시도
        try:
            root = ET.fromstring(raw_clean)
            return self._xml_to_dict(root)
        except Exception as err:
            logger.error("NIMS 응답 파싱 실패: %s (원문: %s)", err, raw_clean[:300])
            raise ValueError(f"NIMS 응답 형식을 해석할 수 없습니다: {raw_clean[:200]}") from err

    def _xml_to_dict(self, node: ET.Element) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for child in node:
            tag = child.tag
            tag_lower = tag.lower()

            if len(child) > 0:
                # <list> 태그이거나 하위 요소들이 <item>, <row>, <bssh> 형태인 경우
                sub_tags = [sub.tag.lower() for sub in child]
                if tag_lower in ("list", "data") or any(st in ("item", "row", "bssh") for st in sub_tags):
                    items = []
                    for sub in child:
                        if len(sub) > 0:
                            item_dict = {elem.tag: (elem.text or "").strip() for elem in sub}
                            items.append(item_dict)
                        else:
                            items.append({sub.tag: (sub.text or "").strip()})
                    data["list"] = items
                else:
                    data[tag] = self._xml_to_dict(child)
            else:
                data[tag] = (child.text or "").strip()
        return data

    def _normalize_result(self, raw: dict[str, Any]) -> dict[str, Any]:
        # NIMS 중첩 응답(response -> header/body) 구조 평탄화
        flat: dict[str, Any] = {}
        if isinstance(raw.get("response"), dict):
            resp = raw["response"]
            if isinstance(resp.get("header"), dict):
                flat.update(resp["header"])
            if isinstance(resp.get("body"), dict):
                flat.update(resp["body"])
            for k, v in resp.items():
                if k not in ("header", "body"):
                    flat[k] = v
        else:
            flat.update(raw)

        # 대소문자 무관하게 키 추출
        lookup = {k.upper(): v for k, v in flat.items()}

        code_val = lookup.get("RESULT_CODE", lookup.get("RESULTCODE", lookup.get("CODE", 0)))
        try:
            result_code = int(code_val)
        except (ValueError, TypeError):
            result_code = -1 if str(code_val) != "0" else 0

        result_msg = str(lookup.get("RESULT_MSG", lookup.get("RESULTMSG", lookup.get("MSG", ""))))
        total_count_val = lookup.get("TOTAL_COUNT", lookup.get("TOTALCOUNT", lookup.get("COUNT", 0)))
        try:
            total_count = int(total_count_val)
        except (ValueError, TypeError):
            total_count = 0

        is_end_yn = str(lookup.get("IS_END_YN", lookup.get("ISENDYN", "Y"))).upper()

        raw_list = lookup.get("LIST", flat.get("list", flat.get("data", [])))
        if isinstance(raw_list, dict):
            raw_list = [raw_list]
        elif not isinstance(raw_list, list):
            raw_list = []

        normalized_items: list[dict[str, Any]] = []
        valid_bssh_cds: list[dict[str, str]] = []

        for item in raw_list:
            if not isinstance(item, dict):
                continue
            item_upper = {k.upper(): (str(v).strip() if v is not None else "") for k, v in item.items()}
            
            bssh_cd = item_upper.get("BSSH_CD", "")
            bssh_nm = item_upper.get("BSSH_NM", "")
            induty_nm = item_upper.get("INDUTY_NM", "")
            hdnt_cd = item_upper.get("HDNT_CD", "")
            hdnt_nm = item_upper.get("HDNT_NM", "")
            bizrno = item_upper.get("BIZRNO", "")
            rprsntv_nm = item_upper.get("RPRSNTV_NM", "")
            chrg_nm = item_upper.get("CHRG_NM", "")
            hptl_no = item_upper.get("HPTL_NO", "")
            join_yn = item_upper.get("JOIN_YN", "")
            bssh_sttus_nm = item_upper.get("BSSH_STTUS_NM", "")
            prmisn_no = item_upper.get("PRMISN_NO", "")

            # 가입 및 정상(승인) 상태 판단: 회원가입 '가입' AND 상태 '승인' 또는 '정상'
            is_joined = join_yn == "가입" or "가입" in join_yn
            is_normal = bssh_sttus_nm in ("승인", "정상") or "승인" in bssh_sttus_nm or "정상" in bssh_sttus_nm
            is_active_valid = is_joined and is_normal

            row_data = {
                "bssh_cd": bssh_cd,
                "bssh_nm": bssh_nm,
                "induty_nm": induty_nm,
                "hdnt_cd": hdnt_cd,
                "hdnt_nm": hdnt_nm,
                "bizrno": bizrno,
                "rprsntv_nm": rprsntv_nm,
                "chrg_nm": chrg_nm,
                "hptl_no": hptl_no,
                "join_yn": join_yn,
                "bssh_sttus_nm": bssh_sttus_nm,
                "prmisn_no": prmisn_no,
                "is_active_valid": is_active_valid,
            }
            normalized_items.append(row_data)

            if is_active_valid and bssh_cd:
                valid_bssh_cds.append({
                    "bssh_cd": bssh_cd,
                    "bssh_nm": bssh_nm,
                    "bizrno": bizrno,
                    "hptl_no": hptl_no,
                })

        return {
            "result_code": result_code,
            "result_msg": result_msg,
            "total_count": total_count if total_count > 0 else len(normalized_items),
            "is_end_yn": is_end_yn,
            "items": normalized_items,
            "valid_bssh_list": valid_bssh_cds,
            "has_valid": len(valid_bssh_cds) > 0,
        }
