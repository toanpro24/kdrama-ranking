"""Update gallery images for all actresses from Wikimedia Commons."""
import hashlib
import urllib.parse
from database import actresses_collection


def wiki_thumb(filename: str, width: int = 400) -> str:
    """Convert a Wikimedia Commons filename to a direct thumbnail URL."""
    # Decode percent-encoded filename, replace spaces with underscores
    name = urllib.parse.unquote(filename).replace(" ", "_")
    md5 = hashlib.md5(name.encode("utf-8")).hexdigest()
    ext = name.rsplit(".", 1)[-1].lower()
    # SVG thumbnails are served as PNG
    suffix = f"{width}px-{name}" if ext != "svg" else f"{width}px-{name}.png"
    return (
        f"https://upload.wikimedia.org/wikipedia/commons/thumb/"
        f"{md5[0]}/{md5[:2]}/{urllib.parse.quote(name)}/{suffix}"
    )


# Raw filenames (decoded) for each actress by name – will be converted to direct URLs
_GALLERY_FILES: dict[str, list[str]] = {
    "Kim Ji-won": [],
    "Jun Ji-hyun": [
        "191112_전지현_(2).jpg",
        "20250902_Jun_Ji-hyun_(전지현).png",
        "JiHyun2009(cropped).jpg",
        "네파_따뜻한_세상_캠페인_전지현_홍보대사_위촉식.jpg",
    ],
    "Song Hye-kyo": [
        "(Marie_Claire_Korea)_THE_Princess_with_Song_Hye_Kyo_(4).jpg",
        "Song_Hye-kyo.jpg",
        "Song_Hye-kyo_송혜교_2022.jpg",
        "Song_Hye_Kyo_2025_송혜교_04.jpg",
        '송혜교,_\u201c봄을_닮은_미소\u201c_(1).jpg',
    ],
    "Park Shin-hye": [
        "(160204)_Park_Shin_Hye_@_the_'DongJu_-_The_Portrait_of_A_Poet'_Movie_Premiere.jpg",
        "120119_서울가요대상-박신혜.jpg",
        "Park_Shin-hye_from_acrofan.jpg",
        "Park_Shin-hye_in_April_2025.png",
        "Park_Shin-hye_in_November_2024.png",
        "Park_Shin-hye_in_September_2024_02.png",
    ],
    "Bae Suzy": [
        "180503_수지_01.jpg",
        "20241128_Bae_Suzy_CELINE_photocall_(cropped).jpg",
        "Bae_Suzy_at_OB_Beer_Hanmac_'As_Smooth_As_Possible'_campaign,_3_April_2024_06.jpg",
        "Suzy_at_the_press_conference_for_Architecture_101_181.jpg",
        "Suzy_departing_from_Incheon_Airport,_26_March_2025_01.png",
        "Suzy_with_her_wax_figure,_Madame_Tussauds_Hong_Kong,_13_September_2016_02.jpg",
    ],
    "IU (Lee Ji-eun)": [],
    "Kim So-hyun": [
        "15.01.24_음악중심_김소현_퇴근길_02.jpg",
        "160924_SOUP_김소현_02.jpg",
        "161231_KBS연기대상_김소현_직찍_(1).jpg",
        "171207_김소현_01.jpg",
        "Kim_So-hyun.jpg",
        "Kim_So-hyun_Airport_Departure_February_2025.png",
    ],
    "Moon Ga-young": [
        "160329_영화_커터_VIP_시사회_06.jpg",
        "20250319_Moon_Ga-young_at_a_photo_call_event_02.jpg",
        "210609_Moon_Ga-young_with_Marie_Claire_Korea_02.png",
        "Moon_Gayoung_at_Dolce&Gabbana_photocall,_24_October_2024_01.png",
    ],
    "Han So-hee": [
        "2017_아시아_모델_페스티벌_레드카펫_(26)_(cropped).jpg",
        "20241108_Han_Sohee_for_BOUCHERON_05.jpg",
        "Han_So-Hee_at_the_2025_Toronto_International_Film_Festival_(cropped).jpg",
    ],
    "Kim Yoo-jung": [],
    "Shin Min-a": [
        "LG_XNOTE_P430_TV광고_사진_-_신민아_&_송중기_(24).jpg",
        "Shin_Min-a_for_Marie_Claire_Korea_December_2018.jpg",
        "Shin_Min-a_in_August_2022.jpg",
        "Shin_Min-a_in_September_2024.png",
    ],
    "Son Ye-jin": [
        "140717_Son_Ye-jin_and_Hyun_Bin_at_18th_Puchon_International_Fantastic_Film_Festival_(cropped).jpg",
        "181018_손예진_04_(cropped).jpg",
        "Son_Ye-jin.png",
        "Son_Ye-jin_in_March_2024.png",
    ],
    "Kim Tae-ri": [
        "161125_제37회_청룡영화상_신인여우상_수상_김태리_직찍_(1).jpg",
        "Kim_Tae-ri_PRADA_BEAUTY_Photo_call_August_2024.png",
        "Kim_Taeri_(김태리)_in_July_2023_03.png",
    ],
    "Jeon Yeo-been": [],
    "Lim Ji-yeon": [
        "Lim_Ji-yeon_at_The_Glory_press_conference_on_201222_(1).png",
        "Lim_Ji-yeon_in_October_2025.png",
        "Lim_Jiyeon_in_2019.png",
        "Lim_Jiyeon_press_conference_The_Tale_of_Lady_Ok_2024.png",
        "Lim_in_2015.png",
    ],
    "Go Min-si": [
        "Go_Min-si_2021.png",
        "고민시와_함께한_뷰티화보_01.png",
    ],
    "Park Bo-young": [
        "151003_부산국제영화제_돌연변이_야외_무대인사_(Park_Bo-young).jpg",
        "189429_박보영_(2).jpg",
        "Park_Bo-young_from_acrofan.jpg",
    ],
    "Seo Ye-ji": [],
    "Nam Ji-hyun": [],
    "Kim Se-jeong": [
        "160904_평촌걷기축제_구구단_세정_직찍_업로드_(3).jpg",
        "189429_'크록스_바이브'_이벤트_홍보대사_세정_(5).jpg",
        "20220226_Kim_Se-jeong_김세정_for_Marie_Claire_Korea.jpg",
        "Gugudan_Sejeong.png",
        "Kim_Sejeong_in_June_2025.png",
        "Sejeong_on_SBS_Radio_on_March_19,_2020_(4).jpg",
    ],
    "Park Min-young": [
        "20250625_Park_Min-young_TAG_Heuer_PhotoCall.jpg",
        "Park_Min-young_May_2018.png",
    ],
    "Shin Hye-sun": [
        "171231_2017_KBS연기대상_레드카펫_신혜선.jpg",
        "Shin_Hye-sun_in_April_2024.png",
    ],
    "Kim Go-eun": [
        "Kim_Go-eun_at_the_2024_Toronto_International_Film_Festival_2.jpg",
        "Kim_Go-eun_in_2020_6.png",
        "Kim_Ko-Eun.jpg",
    ],
    "Lee Sung-kyung": [
        "Lee_Sung-kyung_in_March_2025.png",
        "Lee_Sung-kyung_on_October_18,_2019_at_Jimmy_Choo_event_02.jpg",
    ],
    "Jung So-min": [
        "Jung_So-min_at_the_press_conference_of_SBS_Bad_Guy.jpg",
        "Jung_So-min_in_March_2025.png",
        "Jung_So-min_in_October_2024.png",
    ],
    "Chun Woo-hee": [
        "Chun_Woo-hee_in_July_2024_02.jpg",
        "천우희_at_BIFF_2013.jpg",
    ],
    "Lee Se-young": [
        "Lee_Se-young_at_Incheon_International_Airport_on_28022025_(2).jpg",
    ],
    "Moon Chae-won": [
        "Moon_Chae-won_at_The_Princess'_Man_poster_shooting_163.jpg",
        "Moon_Chae-won_in_2024_-_1.png",
        "제19회_부천국제판타스틱영화제_레드카펫_part.3_16.jpg",
    ],
    "Kim Da-mi": [
        "20240410_Kim_Da-mi_(김다미).jpg",
        "Kim_Dami_20180830.jpg",
    ],
    "Hwang Jung-eum": [
        "Hwang_Jung-Eum_in_2009_(2).jpg",
        "Hwang_Jung-eum_in_June_2017.jpg",
        "Hwang_Jung-eum_in_March_2024.png",
    ],
    "Kim Hye-yoon": [
        "20250820_Kim_Hye_Yoon_(김혜윤).png",
        "Kim_Hye-yoon_김혜윤_2022.jpg",
        "Kim_hye_yoon_2019_10_02.jpg",
        "김혜윤_Airport_Departure_06082024.jpg",
    ],
    "Lee Bo-young": [
        "492d5bec01aecbbeffbb66aa8b3681a2--brunettes-lee-bo-young.jpg",
        "Choi_Ki-Hwan_and_Lee_Bo-Young_(cropped).jpg",
        "Lee_Bo-Young.jpg",
        "Lee_Bo-young_in_March_2024.png",
    ],
    "Gong Hyo-jin": [
        'Gong_Hyo-jin_at_"The_Producers"_press_conference_(May_2015).jpg',
        "Gong_Hyo-jin_in_October_2024.png",
        "Kong_Hyo-Jin.jpg",
    ],
    "Ha Ji-won": [
        "Ha_Ji-Won_in_2009.jpg",
        "Ha_Ji-won_at_the_premiere_of_Miracle_on_1st_Street_116.jpg",
        "Ha_Ji-won_in_September_2025.png",
        "Ha_Ji-won_on_26_July_2011_(4).jpg",
    ],
    "Jang Na-ra": [
        "191025_장나라.jpg",
        "Jang_Na-ra_in_July_2017.jpg",
        "Jang_Na-ra_in_July_2024.png",
    ],
    "Seo Hyun-jin": [],
}

# Build the final gallery with proper direct URLs
GALLERY = {
    name: [wiki_thumb(f) for f in files]
    for name, files in _GALLERY_FILES.items()
}


def update():
    count = 0
    for actress_name, photos in GALLERY.items():
        if not photos:
            # For actresses with no wiki photos, use their main image as gallery
            doc = actresses_collection.find_one({"name": actress_name})
            if doc and doc.get("image"):
                photos = [doc["image"]]
        result = actresses_collection.update_one(
            {"name": actress_name},
            {"$set": {"gallery": photos}},
        )
        if result.matched_count > 0:
            count += 1
    print(f"Updated gallery for {count} actresses.")


if __name__ == "__main__":
    update()
