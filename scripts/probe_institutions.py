"""기관 채용 URL 배치 프로빙 스크립트."""
import requests
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
H = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"}

# (기관명, slug_or_direct_url)
# recruiter.co.kr 패턴: https://{slug}.recruiter.co.kr/career/home
# greetinghr 패턴: https://{slug}.career.greetinghr.com/
INSTITUTIONS = {
    # 규제/중앙기관
    "한국은행": "https://www.bok.or.kr/portal/bbs/P0000559/list.do?menuNo=200690",
    "금융감독원": "https://fss.recruiter.co.kr/career/home",
    "금융위원회": "https://fsc.recruiter.co.kr/career/home",
    "전국은행연합회": "https://kfb.recruiter.co.kr/career/home",
    "금융투자협회": "https://www.kofia.or.kr/brd/m_73/list.do",
    "손해보험협회": "https://knia.recruiter.co.kr/career/home",
    "생명보험협회": "https://klia.recruiter.co.kr/career/home",
    "여신금융협회": "https://crefia.recruiter.co.kr/career/home",
    "저축은행중앙회": "https://fsb.recruiter.co.kr/career/home",
    "신용협동조합중앙회": "https://cu.recruiter.co.kr/career/home",
    "새마을금고중앙회": "https://kfcc.recruiter.co.kr/career/home",
    "한국거래소": "https://recruit.krx.co.kr/",
    "한국증권금융": "https://ksfc.recruiter.co.kr/career/home",
    "한국예탁결제원": "https://ksd.recruiter.co.kr/career/home",
    "코스콤": "https://recruit.koscom.com/",
    "금융결제원": "https://kftc.recruiter.co.kr/career/home",
    "금융보안원": "https://fsa.recruiter.co.kr/career/home",
    "한국신용정보원": "https://kcredit.recruiter.co.kr/career/home",
    "서울외국환중개": "https://smbs.recruiter.co.kr/career/home",
    "한국자금중개": "https://kfb2.recruiter.co.kr/career/home",
    # 공제회
    "한국교직원공제회": "https://ktcu.recruiter.co.kr/career/home",
    "군인공제회": "https://mac.recruiter.co.kr/career/home",
    "경찰공제회": "https://poba.recruiter.co.kr/career/home",
    "대한지방행정공제회": "https://loginet.recruiter.co.kr/career/home",
    "건설공제조합": "https://cgc.recruiter.co.kr/career/home",
    "과학기술인공제회": "https://sema.recruiter.co.kr/career/home",
    # 정책금융
    "한국산업은행": "https://kdb.recruiter.co.kr/career/home",
    "한국수출입은행": "https://koreaexim.recruiter.co.kr/career/home",
    "중소기업은행": "https://ibk.recruiter.co.kr/career/home",
    "신용보증기금": "https://kodit.recruiter.co.kr/career/home",
    "기술보증기금": "https://kibo.recruiter.co.kr/career/home",
    "한국주택금융공사": "https://hf.recruiter.co.kr/career/home",
    "한국자산관리공사": "https://kamco.recruiter.co.kr/career/home",
    "예금보험공사": "https://kdic.recruiter.co.kr/career/home",
    "한국투자공사": "https://recruit.kic.com/",
    "한국무역보험공사": "https://ksure.recruiter.co.kr/career/home",
    "주택도시보증공사": "https://hug.recruiter.co.kr/career/home",
    "서울보증보험": "https://sgi.recruiter.co.kr/career/home",
    "한국해양진흥공사": "https://kobc.recruiter.co.kr/career/home",
    "서민금융진흥원": "https://kinfa.recruiter.co.kr/career/home",
    "농업정책보험금융원": "https://apfs.recruiter.co.kr/career/home",
    # 시중은행
    "KB국민은행": "https://kbstar.recruiter.co.kr/career/home",
    "신한은행": "https://shinhan.recruiter.co.kr/career/home",
    "하나은행": "https://hanabank.recruiter.co.kr/career/home",
    "우리은행": "https://wooribank.recruiter.co.kr/career/home",
    "NH농협은행": "https://nhrecruit.co.kr/",
    "부산은행": "https://busanbank.recruiter.co.kr/career/home",
    "경남은행": "https://knbank.recruiter.co.kr/career/home",
    "iM뱅크": "https://imbank.recruiter.co.kr/career/home",
    "광주은행": "https://kjbank.recruiter.co.kr/career/home",
    "전북은행": "https://jbbank.recruiter.co.kr/career/home",
    "제주은행": "https://jejubank.recruiter.co.kr/career/home",
    "Sh수협은행": "https://shbank.recruiter.co.kr/career/home",
    "카카오뱅크": "https://kakaobank.recruiter.co.kr/career/home",
    "토스뱅크": "https://recruit.tossbank.com/",
    "케이뱅크": "https://kbank.career.greetinghr.com/",
    "한국씨티은행": "https://citibank.recruiter.co.kr/career/home",
    "SC제일은행": "https://scbank.recruiter.co.kr/career/home",
    # 증권사
    "미래에셋증권": "https://recruit.miraeasset.com/",
    "한국투자증권": "https://truefriend.recruiter.co.kr/career/home",
    "NH투자증권": "https://nhqv.recruiter.co.kr/career/home",
    "삼성증권": "https://samsungsec.recruiter.co.kr/career/home",
    "KB증권": "https://kbsec.recruiter.co.kr/career/home",
    "하나증권": "https://hanasec.recruiter.co.kr/career/home",
    "메리츠증권": "https://meritz.recruiter.co.kr/career/home",
    "신한투자증권": "https://shinhansec.recruiter.co.kr/career/home",
    "키움증권": "https://kiwoom.recruiter.co.kr/career/home",
    "대신증권": "https://www.daishin.com/g.ds?m=4027&p=3979&v=2983",
    "교보증권": "https://kyobo.recruiter.co.kr/career/home",
    "한화투자증권": "https://hanwhasec.recruiter.co.kr/career/home",
    "유안타증권": "https://yuanta.recruiter.co.kr/career/home",
    "유진투자증권": "https://eugenefn.recruiter.co.kr/career/home",
    "현대차증권": "https://hmcsec.recruiter.co.kr/career/home",
    "하이투자증권": "https://hiinvest.recruiter.co.kr/career/home",
    "IBK투자증권": "https://ibkis.recruiter.co.kr/career/home",
    "DB금융투자": "https://dbfi.recruiter.co.kr/career/home",
    "SK증권": "https://sksec.recruiter.co.kr/career/home",
    "신영증권": "https://shinyoung.recruiter.co.kr/career/home",
    "한양증권": "https://hanyang.recruiter.co.kr/career/home",
    "BNK투자증권": "https://bnkis.recruiter.co.kr/career/home",
    "흥국증권": "https://heungkuksec.recruiter.co.kr/career/home",
    "다올투자증권": "https://daol.recruiter.co.kr/career/home",
    "부국증권": "https://bookook.recruiter.co.kr/career/home",
    # 선물사
    "삼성선물": "https://samsungfutures.recruiter.co.kr/career/home",
    "NH선물": "https://nhfutures.recruiter.co.kr/career/home",
    "하나선물": "https://hanafutures.recruiter.co.kr/career/home",
    "키움선물": "https://kiwoomfutures.recruiter.co.kr/career/home",
    # 생명보험
    "삼성생명": "https://recruit.samsunglife.com/",
    "한화생명": "https://hanwhalife.recruiter.co.kr/career/home",
    "교보생명": "https://kyobogen.recruiter.co.kr/career/home",
    "신한라이프": "https://shinhanlife.recruiter.co.kr/career/home",
    "NH농협생명": "https://nhlife.recruiter.co.kr/career/home",
    "하나생명": "https://hanalife.recruiter.co.kr/career/home",
    "KB라이프생명": "https://kblife.recruiter.co.kr/career/home",
    "동양생명": "https://dylife.recruiter.co.kr/career/home",
    "미래에셋생명": "https://miraeassetlife.recruiter.co.kr/career/home",
    "ABL생명": "https://abllife.recruiter.co.kr/career/home",
    "KDB생명": "https://kdblife.recruiter.co.kr/career/home",
    # 손해보험
    "삼성화재": "https://samsungfire.recruiter.co.kr/career/home",
    "현대해상": "https://hiins.recruiter.co.kr/career/home",
    "DB손해보험": "https://dbins.recruiter.co.kr/career/home",
    "KB손해보험": "https://kbinsure.recruiter.co.kr/career/home",
    "메리츠화재": "https://meritzfire.recruiter.co.kr/career/home",
    "한화손해보험": "https://hanwhageneral.recruiter.co.kr/career/home",
    "롯데손해보험": "https://lotteins.recruiter.co.kr/career/home",
    "흥국화재": "https://heungkukfire.recruiter.co.kr/career/home",
    "농협손해보험": "https://nhfire.recruiter.co.kr/career/home",
    "캐롯손해보험": "https://carrotins.recruiter.co.kr/career/home",
    "코리안리": "https://koreanre.recruiter.co.kr/career/home",
    # 카드
    "신한카드": "https://shinhancard.recruiter.co.kr/career/home",
    "삼성카드": "https://samsungcard.recruiter.co.kr/career/home",
    "KB국민카드": "https://kbcard.recruiter.co.kr/career/home",
    "현대카드": "https://recruit.hyundaicard.com/",
    "롯데카드": "https://lottecard.recruiter.co.kr/career/home",
    "우리카드": "https://wooricard.recruiter.co.kr/career/home",
    "비씨카드": "https://bccard.recruiter.co.kr/career/home",
    "하나카드": "https://hanacard.recruiter.co.kr/career/home",
    # 캐피탈
    "현대캐피탈": "https://recruit.hyundaicapital.com/",
    "KB캐피탈": "https://kbcapital.recruiter.co.kr/career/home",
    "하나캐피탈": "https://hanacapital.recruiter.co.kr/career/home",
    "신한캐피탈": "https://shinhancapital.recruiter.co.kr/career/home",
    "우리금융캐피탈": "https://wooricapital.recruiter.co.kr/career/home",
    "아주캐피탈": "https://ajucapital.recruiter.co.kr/career/home",
    "롯데캐피탈": "https://lottecapital.recruiter.co.kr/career/home",
    "BNK캐피탈": "https://bnkcapital.recruiter.co.kr/career/home",
    "JB우리캐피탈": "https://jbwooricapital.recruiter.co.kr/career/home",
    "NH농협캐피탈": "https://nhcapital.recruiter.co.kr/career/home",
    "DGB캐피탈": "https://dgbcapital.recruiter.co.kr/career/home",
    "메리츠캐피탈": "https://meritzcapital.recruiter.co.kr/career/home",
    # 저축은행
    "SBI저축은행": "https://sbisavings.recruiter.co.kr/career/home",
    "OK저축은행": "https://oksavings.recruiter.co.kr/career/home",
    "웰컴저축은행": "https://welcomesavings.recruiter.co.kr/career/home",
    "페퍼저축은행": "https://peppersavings.recruiter.co.kr/career/home",
    "애큐온저축은행": "https://aquon.recruiter.co.kr/career/home",
    "한국투자저축은행": "https://kitb.recruiter.co.kr/career/home",
    "JT저축은행": "https://jtsavings.recruiter.co.kr/career/home",
    # 자산운용
    "미래에셋자산운용": "https://miraeassetam.recruiter.co.kr/career/home",
    "한국투자신탁운용": "https://kitam.recruiter.co.kr/career/home",
    "삼성자산운용": "https://samsungam.recruiter.co.kr/career/home",
    "KB자산운용": "https://kbam.recruiter.co.kr/career/home",
    "신한자산운용": "https://shinhanam.recruiter.co.kr/career/home",
    "한화자산운용": "https://hanwaaim.recruiter.co.kr/career/home",
    "키움투자자산운용": "https://kiwoomam.recruiter.co.kr/career/home",
    "신영자산운용": "https://shinyoungam.recruiter.co.kr/career/home",
    # PE/VC
    "한국벤처투자": "https://kvic.recruiter.co.kr/career/home",
    "한국성장금융": "https://kgf.recruiter.co.kr/career/home",
    # 핀테크
    "토스": "https://toss.im/career",
    "카카오페이": "https://kakaopay.career.greetinghr.com/",
    "핀다": "https://finda.co.kr/",
    "레이니스트": "https://rainist.com/jobs",
    "페이코": "https://payco.recruiter.co.kr/career/home",
}


def probe(args):
    name, url = args
    try:
        r = requests.get(url, headers=H, timeout=7, verify=False, allow_redirects=True)
        ok = r.status_code == 200 and len(r.content) > 2000
        return name, url, ok, r.status_code, len(r.content)
    except Exception as e:
        return name, url, False, None, 0


results = {}
with ThreadPoolExecutor(max_workers=20) as ex:
    for name, url, ok, code, size in ex.map(probe, INSTITUTIONS.items()):
        results[name] = (url if ok else None, code, size)
        print(f'{"V" if ok else "X"} {name}: {code} {size}b {url}')

print("\n=== WORKING URLS ===")
working = {k: v[0] for k, v in results.items() if v[0]}
for name, url in sorted(working.items()):
    print(f'"{name}": "{url}",')

print(f"\nTotal: {len(working)}/{len(INSTITUTIONS)} working")
