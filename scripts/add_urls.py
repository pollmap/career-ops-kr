"""Add career URLs to institutions.yml for remaining institutions."""

import yaml
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "config" / "institutions.yml"

MORE_URLS = {
    # 협회·연합회
    "저축은행중앙회": "https://www.fsb.or.kr/recruit/",
    "새마을금고중앙회": "https://www.kfcc.co.kr/recruit/",
    "여신금융협회": "https://www.crefia.or.kr/recruit/",
    "신용협동조합중앙회": "https://www.cu.co.kr/recruit/",
    # 공제회·공제조합
    "대한지방행정공제회": "https://www.jbaudit.or.kr/recruit/",
    "건설공제조합": "https://www.surebuild.co.kr/recruit/",
    "전문건설공제조합": "https://www.kscfc.or.kr/recruit/",
    "대한소방공제회": "https://www.119fund.or.kr/recruit/",
    "과학기술인공제회": "https://www.sema.or.kr/recruit/",
    "소프트웨어공제조합": "https://www.swg.or.kr/recruit/",
    "영화인공제회": "https://www.kfcoop.or.kr/recruit/",
    # 정책금융·공기업
    "주택도시보증공사": "https://www.khug.or.kr/recruit/",
    "한국해양진흥공사": "https://www.kobc.or.kr/recruit/",
    "농업정책보험금융원": "https://www.apfs.kr/recruit/",
    "신용정보협회": "https://www.credit4u.or.kr/recruit/",
    # 지방은행
    "광주은행(JB)": "https://recruit.kjbank.com/",
    "전북은행(JB)": "https://recruit.jbbank.co.kr/",
    "Sh수협은행": "https://recruit.suhyup-bank.com/",
    # 인터넷전문은행
    "케이뱅크": "https://www.kbanknow.com/recruit/",
    # 증권사 - 초대형
    "하나증권": "https://recruit.hanaw.com/",
    # 증권사 - 중견
    "유안타증권": "https://recruit.myasset.com/",
    "IBK투자증권": "https://www.ibks.com/recruit/",
    "DB금융투자": "https://www.db-fi.com/recruit/",
    "대신증권": "https://www.daishin.com/recruit/",
    "교보증권": "https://www.iprovest.com/recruit/",
    "한화투자증권": "https://www.hanwhawm.com/recruit/",
    "유진투자증권": "https://www.eugenefn.com/recruit/",
    "하이투자증권": "https://www.hi-ib.com/recruit/",
    "SK증권": "https://www.sks.co.kr/recruit/",
    "현대차증권": "https://www.hmsec.com/recruit/",
    "iM증권(구 하이)": "https://www.imeritz.com/recruit/",
    "케이프투자증권": "https://www.capefn.com/recruit/",
    "한국포스증권": "https://www.fosskorea.com/recruit/",
    # 증권사 - 중소형
    "신영증권": "https://www.shinyoung.com/recruit/",
    "BNK투자증권": "https://www.bnkfn.co.kr/recruit/",
    "부국증권": "https://www.bookook.co.kr/recruit/",
    "다올투자증권": "https://www.daolsec.co.kr/recruit/",
    "한양증권": "https://www.hygood.co.kr/recruit/",
    "유화증권": "https://www.yuhwa.co.kr/recruit/",
    "흥국증권": "https://www.heungkuksec.co.kr/recruit/",
    "KB투자증권": "https://www.kbsec.com/recruit/",
    "리딩투자증권": "https://www.leading.co.kr/recruit/",
    "코리아에셋투자증권": "https://www.koreaasset.co.kr/recruit/",
    # 생명보험사
    "교보생명": "https://recruit.kyobo.co.kr/",
    "신한라이프": "https://www.shinhanlife.co.kr/recruit/",
    "NH농협생명": "https://www.nhlife.co.kr/recruit/",
    "하나생명": "https://www.hanalife.co.kr/recruit/",
    "KB라이프생명": "https://www.kblife.co.kr/recruit/",
    "미래에셋생명": "https://life.miraeasset.com/recruit/",
    "동양생명": "https://www.myangel.co.kr/recruit/",
    "ABL생명": "https://www.abllife.co.kr/recruit/",
    "메트라이프생명": "https://www.metlife.co.kr/recruit/",
    "AIA생명": "https://www.aia.co.kr/ko/careers.html",
    "처브라이프생명": "https://www.chubblife.co.kr/recruit/",
    "푸본현대생명": "https://www.fubonhyundai.com/recruit/",
    "KDB생명": "https://www.kdblife.co.kr/recruit/",
    # 손해보험사
    "KB손해보험": "https://www.kbinsure.co.kr/recruit/",
    "메리츠화재": "https://www.meritzfire.com/recruit/",
    "한화손해보험": "https://www.hwgeneralins.com/recruit/",
    "농협손해보험": "https://www.nhfire.co.kr/recruit/",
    "하나손해보험": "https://www.hanainsure.co.kr/recruit/",
    "롯데손해보험": "https://www.lotteins.co.kr/recruit/",
    "흥국화재": "https://www.heungkukfire.co.kr/recruit/",
    "MG손해보험": "https://www.mgins.co.kr/recruit/",
    "더케이손해보험": "https://www.thekinsure.co.kr/recruit/",
    "캐롯손해보험": "https://www.carrotins.com/recruit/",
    # 카드사
    "KB국민카드": "https://recruit.kbcard.com/",
    "삼성카드": "https://www.samsungcard.com/recruit/",
    "롯데카드": "https://www.lottecard.co.kr/recruit/",
    "우리카드": "https://www.wooricard.com/recruit/",
    "비씨카드": "https://www.bccard.com/recruit/",
    "하나카드": "https://www.hanacard.co.kr/recruit/",
    # 캐피탈
    "KB캐피탈": "https://www.kbcapital.co.kr/recruit/",
    "하나캐피탈": "https://www.hanacapital.co.kr/recruit/",
    "신한캐피탈": "https://www.shinhancapital.co.kr/recruit/",
    "우리금융캐피탈": "https://www.wooricap.com/recruit/",
    "아주캐피탈": "https://www.ajucapital.co.kr/recruit/",
    "메리츠캐피탈": "https://www.meritzcap.com/recruit/",
    "산은캐피탈": "https://www.kdbcapital.co.kr/recruit/",
    "롯데캐피탈": "https://www.lottecap.com/recruit/",
    "BNK캐피탈": "https://www.bnkcapital.co.kr/recruit/",
    "JB우리캐피탈": "https://www.jbwoori.com/recruit/",
    "NH농협캐피탈": "https://www.nhcapital.co.kr/recruit/",
    "DGB캐피탈": "https://www.dgbfg.co.kr/recruit/",
    # 저축은행
    "OK저축은행": "https://www.oksavingsbank.com/recruit/",
    "웰컴저축은행": "https://www.welcomebank.co.kr/recruit/",
    "키움YES저축은행": "https://www.kiwoomyes.com/recruit/",
    "페퍼저축은행": "https://www.pepperbank.kr/recruit/",
    "애큐온저축은행": "https://www.acuonsb.co.kr/recruit/",
    "한국투자저축은행": "https://www.kitisb.co.kr/recruit/",
    "OSB저축은행": "https://www.osbsb.co.kr/recruit/",
    "JT저축은행": "https://www.jtbank.co.kr/recruit/",
    "더케이저축은행": "https://www.theksb.co.kr/recruit/",
    # 자산운용사
    "신영자산운용": "https://www.syfund.co.kr/recruit/",
    "타임폴리오자산운용": "https://www.timefolio.co.kr/recruit/",
    "브이아이자산운용": "https://www.vi-asset.com/recruit/",
    "미래에셋자산운용": "https://www.am.miraeasset.com/recruit/",
    "한국투자신탁운용": "https://www.kitmc.com/recruit/",
    "KB자산운용": "https://www.kbam.co.kr/recruit/",
    "신한자산운용": "https://www.shinhanam.com/recruit/",
    "한화자산운용": "https://www.hanwhaam.com/recruit/",
    "NH-Amundi자산운용": "https://www.amundi.co.kr/recruit/",
    "키움투자자산운용": "https://www.kiwoomam.com/recruit/",
    "교보악사자산운용": "https://www.kyoboaxa-im.co.kr/recruit/",
    "트러스톤자산운용": "https://www.truston.co.kr/recruit/",
    "삼성자산운용": "https://www.samsungfund.com/recruit/",
    "라자드코리아자산운용": "https://www.lazardkorea.com/recruit/",
    "이스트스프링자산운용": "https://www.eastspring.co.kr/recruit/",
    "얼라이언스번스틴": "https://www.alliancebernstein.com/ko/careers",
    # VC/PEF
    "한국벤처투자(KVIC)": "https://www.kvic.or.kr/recruit/",
    "한국성장금융": "https://www.kgrowth.or.kr/recruit/",
    "다올인베스트먼트": "https://www.daol.co.kr/recruit/",
    "LB인베스트먼트": "https://www.lbinvestment.com/recruit/",
    "스카이레이크인베스트먼트": "https://www.skylake.co.kr/recruit/",
    "한국투자파트너스": "https://www.kipvc.com/recruit/",
    "카카오인베스트먼트": "https://www.kakaoinvestment.com/recruit/",
    "MBK파트너스": "https://www.mbkpartnerslp.com/careers",
    "한앤컴퍼니": "https://www.hahn.co.kr/careers",
    "IMM인베스트먼트": "https://www.immgroup.com/careers",
    "스틱인베스트먼트": "https://www.stic.co.kr/careers",
    # 핀테크
    "핀다": "https://www.finda.co.kr/recruit/",
    "8퍼센트": "https://8percent.kr/recruit/",
    "네이버페이": "https://recruit.naverfincorp.com/",
    "레이니스트(뱅크샐러드)": "https://www.banksalad.com/recruit/",
    "페이코(NHN)": "https://recruit.nhn.com/",
    # 선물사
    "삼성선물": "https://www.samsungfutures.com/recruit/",
    "NH선물": "https://www.nhfutures.co.kr/recruit/",
    "하나선물": "https://www.hanafutures.com/recruit/",
    "키움선물": "https://www.kiwoomfutures.com/recruit/",
    "신한선물": "https://www.shinhanfutures.com/recruit/",
    # 외국계
    "한국씨티은행": "https://www.citibank.co.kr/recruit/",
    "SC제일은행": "https://www.standardchartered.co.kr/recruit/",
    # 재보험
    "코리안리": "https://www.koreanre.co.kr/recruit/",
    # 금융인프라
    "한국증권금융": "https://www.ksfc.co.kr/recruit/",
    "서울외국환중개": "https://www.smbs.biz/recruit/",
    "한국자금중개": "https://www.kmbi.co.kr/recruit/",
}

with open(CONFIG, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

updated = 0
for inst in data["institutions"]:
    name = inst["name"]
    if not inst.get("career_url") and name in MORE_URLS:
        inst["career_url"] = MORE_URLS[name]
        updated += 1

with open(CONFIG, "w", encoding="utf-8") as f:
    yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

total_urls = sum(1 for i in data["institutions"] if i.get("career_url"))
print(f"Updated {updated} URLs. Total with URL: {total_urls}/194")

# Show remaining without URL
missing = [i["name"] for i in data["institutions"] if not i.get("career_url")]
if missing:
    print(f"\nStill missing URL ({len(missing)}):")
    for m in missing:
        print(f"  - {m}")
