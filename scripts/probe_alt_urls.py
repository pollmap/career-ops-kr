"""주요 기업 대안 URL 프로빙."""
import requests
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
H = {"User-Agent": UA}

# 개별 기업 공식 채용 페이지 URL 후보 (직접 조사)
ALT_URLS = {
    "KB국민은행": [
        "https://career.kbstar.com/",
        "https://www.kbstar.com/quics?page=C101037",
        "https://kbstar.career.greetinghr.com/",
    ],
    "NH농협은행": [
        "https://nhrecruit.co.kr/",
        "https://www.nonghyup.com/cms/contents/C0000056.do",
        "https://nhbank.career.greetinghr.com/",
    ],
    "우리은행": [
        "https://recruit.wooribank.com/",
        "https://woori.career.greetinghr.com/",
        "https://www.wooribank.com/wb/WOCT0002/WOCT000207M0",
    ],
    "iM뱅크": [
        "https://imbank.career.greetinghr.com/",
        "https://www.imbank.co.kr/user/main/main.do",
        "https://dgb.recruiter.co.kr/career/home",
    ],
    "광주은행": [
        "https://kjbank.career.greetinghr.com/",
        "https://www.kjbank.com/kjbank/about/recruit",
    ],
    "Sh수협은행": [
        "https://shfb.career.greetinghr.com/",
        "https://www.sh.co.kr/main/sub.action?menucd=MENU_0000000056",
    ],
    "케이뱅크": [
        "https://kbank.recruiter.co.kr/career/home",
        "https://www.kbanknow.com/ib20/mnu/FPFLT0000005",
    ],
    "미래에셋증권": [
        "https://miraeasset.recruiter.co.kr/career/home",
        "https://career.miraeasset.com/",
        "https://www.miraeasset.com/about/social/talent/",
    ],
    "삼성증권": [
        "https://recruit.samsungsec.com/",
        "https://www.samsungsecurities.com/recruit/main.do",
        "https://samsungsec.recruiter.co.kr/career/home",
    ],
    "신한투자증권": [
        "https://careers.shinhanib.com/",
        "https://shinhansec.career.greetinghr.com/",
        "https://www.shinhaninvest.com/siib/company/recruit/",
    ],
    "키움증권": [
        "https://kiwoomsec.recruiter.co.kr/career/home",
        "https://recruit.kiwoom.com/",
        "https://kiwoom.career.greetinghr.com/",
    ],
    "한화투자증권": [
        "https://recruit.hanwhainvest.com/",
        "https://hanwhainvest.recruiter.co.kr/career/home",
    ],
    "교보증권": [
        "https://kyobosec.recruiter.co.kr/career/home",
        "https://recruit.kyobosec.com/",
    ],
    "유안타증권": [
        "https://yuanta.career.greetinghr.com/",
        "https://recruit.yuanta.com/",
    ],
    "하나증권": [
        "https://hanasec.career.greetinghr.com/",
        "https://recruit.hana.com/",
        "https://www.hanaw.com/main/recruit/listRecruit.cmd",
    ],
    "삼성생명": [
        "https://samsunglife.recruiter.co.kr/career/home",
        "https://recruit.samsunglife.com/recruit/",
        "https://samsunglife.career.greetinghr.com/",
    ],
    "한화생명": [
        "https://recruit.hanwhalife.com/",
        "https://hanwhalife.career.greetinghr.com/",
        "https://www.hanwhalife.com/recruit/",
    ],
    "교보생명": [
        "https://recruit.kyobo.co.kr/",
        "https://kyobo.career.greetinghr.com/",
        "https://www.kyobo.co.kr/recruit/",
    ],
    "삼성화재": [
        "https://recruit.samsungfire.com/",
        "https://samsungfire.career.greetinghr.com/",
        "https://www.samsungfire.com/fire/recruit/",
    ],
    "현대해상": [
        "https://recruit.hi.co.kr/",
        "https://hiins.career.greetinghr.com/",
        "https://www.hi.co.kr/index/HI_INDEX.html",
    ],
    "DB손해보험": [
        "https://recruit.idongbu.com/",
        "https://dbins.career.greetinghr.com/",
        "https://www.idongbu.com/NLDMBBS/BBS_MNG/bbs_view.asp",
    ],
    "현대카드": [
        "https://career.hyundaicard.com/",
        "https://hyundaicard.career.greetinghr.com/",
        "https://www.hyundaicard.com/cpc/um/CPNUM0048M.do",
    ],
    "현대캐피탈": [
        "https://career.hyundaicapital.com/",
        "https://hyundaicapital.career.greetinghr.com/",
    ],
    "한국수출입은행": [
        "https://www.koreaexim.go.kr/site/main/job",
        "https://koreaexim.career.greetinghr.com/",
        "https://recruit.koreaexim.go.kr/",
    ],
    "한국산업은행": [
        "https://www.kdb.co.kr/hECRC000.do",
        "https://kdb.career.greetinghr.com/",
        "https://recruit.kdb.co.kr/",
    ],
    "신용보증기금": [
        "https://www.kodit.co.kr/kodit/sm/smb/bbs/selectBbsList.do?bbsId=RECRUIT_NOTICE",
        "https://kodit.career.greetinghr.com/",
    ],
    "예금보험공사": [
        "https://www.kdic.or.kr/intro/emp/list.do",
        "https://kdic.career.greetinghr.com/",
    ],
    "서울보증보험": [
        "https://recruit.sgi.co.kr/",
        "https://sgi.career.greetinghr.com/",
        "https://www.sgi.co.kr/contents/careers",
    ],
    "한국거래소": [
        "https://recruit.krx.co.kr/",
        "https://krx.recruiter.co.kr/career/home",
        "https://www.krx.co.kr/recruitment/index.html",
    ],
    "한국예탁결제원": [
        "https://ksd.recruiter.co.kr/career/home",
        "https://recruit.ksd.or.kr/",
        "https://www.ksd.or.kr/ko/ksd/career/recruitment",
    ],
    "금융감독원": [
        "https://www.fss.or.kr/fss/com/rcrt/list.do",
        "https://fss.career.greetinghr.com/",
        "https://recruit.fss.or.kr/",
    ],
    "한국자산관리공사": [
        "https://www.kamco.or.kr/portal/Contents.do?menucd=MENU03030000000",
        "https://kamco.career.greetinghr.com/",
    ],
    "한국무역보험공사": [
        "https://www.ksure.or.kr/main/aboutus/managementRecruit.do",
        "https://ksure.career.greetinghr.com/",
    ],
    "주택도시보증공사": [
        "https://www.hug.go.kr/hug/bbs/BBS00039/list.do",
        "https://hug.career.greetinghr.com/",
        "https://hug.recruiter.co.kr/career/home",
    ],
    "한국해양진흥공사": [
        "https://www.kobc.or.kr/hmpg/cont/recrt/List.do",
        "https://kobc.career.greetinghr.com/",
    ],
    "서민금융진흥원": [
        "https://www.kinfa.or.kr/main/kinfa/info/emp_recruit/list.do",
        "https://kinfa.career.greetinghr.com/",
    ],
    "한국주택금융공사": [
        "https://www.hf.go.kr/ko/sub05/page_022.do",
        "https://hf.career.greetinghr.com/",
    ],
    "기술보증기금": [
        "https://www.kibo.or.kr/websquare/websquare.html?w2xPath=/com/recruit/recruitList.xml",
        "https://kibo.career.greetinghr.com/",
    ],
    "금융결제원": [
        "https://www.kftc.or.kr/kftc/main/EgovKFTCRecruitList.do",
        "https://kftc.career.greetinghr.com/",
    ],
    "금융보안원": [
        "https://www.fsec.or.kr/user/main/main.do",
        "https://fsec.recruiter.co.kr/career/home",
        "https://fsec.career.greetinghr.com/",
    ],
    "한국신용정보원": [
        "https://www.kcredit.or.kr/main/sub/recru.do",
        "https://kcredit.career.greetinghr.com/",
    ],
    "한국교직원공제회": [
        "https://www.ktcu.or.kr/main/contents.do?menuNo=200146",
        "https://ktcu.career.greetinghr.com/",
    ],
    "한국증권금융": [
        "https://www.ksfc.co.kr/company/recruit/recruitList.asp",
        "https://ksfc.career.greetinghr.com/",
    ],
    "SC제일은행": [
        "https://www.standardchartered.co.kr/np/kr/pmc/aboutsc/CareerMain.jsp",
        "https://scb.career.greetinghr.com/",
    ],
    "한국씨티은행": [
        "https://www.citibank.co.kr/personal/about/career/",
        "https://citikorea.career.greetinghr.com/",
    ],
    "SBI저축은행": [
        "https://www.sbisavingsbank.com/user/main/main.do",
        "https://sbisb.recruiter.co.kr/career/home",
    ],
    "OK저축은행": [
        "https://www.oksavingsbank.com/company/talent/index.do",
        "https://okbank.recruiter.co.kr/career/home",
    ],
    "웰컴저축은행": [
        "https://www.welcomebank.co.kr/ib20/mnu/WB0000007",
        "https://welcomesb.recruiter.co.kr/career/home",
    ],
    "페퍼저축은행": [
        "https://www.pepperbank.co.kr/company/talent.do",
        "https://pepperbank.recruiter.co.kr/career/home",
    ],
}


def probe_list(name, urls):
    for url in urls:
        try:
            r = requests.get(url, headers=H, timeout=6, verify=False, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 3000:
                return name, url, r.status_code, len(r.content)
        except Exception:
            continue
    return name, None, None, 0


results = {}
with ThreadPoolExecutor(max_workers=15) as ex:
    futures = {ex.submit(probe_list, name, urls): name for name, urls in ALT_URLS.items()}
    for f in as_completed(futures):
        name, url, code, size = f.result()
        results[name] = url
        print(f'{"V" if url else "X"} {name}: {url} ({size}b)' if url else f'X {name}: not found')

print("\n=== ADDITIONAL WORKING URLS ===")
for name, url in sorted(results.items()):
    if url:
        print(f'"{name}": "{url}",')
print(f"\nAdditional: {sum(1 for u in results.values() if u)}")
