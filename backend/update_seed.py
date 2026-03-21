"""Add poster URLs and gallery images to seed data, then re-seed."""
import json
from database import actresses_collection

POSTERS = {
    "My Liberation Notes": "https://upload.wikimedia.org/wikipedia/en/5/5f/My_Liberation_Notes_%282022_television_series%29.jpg",
    "Lovestruck in the City": "https://upload.wikimedia.org/wikipedia/en/0/0d/City_Couple%E2%80%99s_Way_of_Love_My_Lovable_Camera_Thief.jpg",
    "Arthdal Chronicles": "https://upload.wikimedia.org/wikipedia/en/3/3a/Arthdalchronicles.jpg",
    "Fight for My Way": "https://upload.wikimedia.org/wikipedia/en/d/d4/Fight_For_My_Way_Poster.jpg",
    "Descendants of the Sun": "https://upload.wikimedia.org/wikipedia/en/6/6e/DescendantsoftheSun.jpg",
    "Jirisan": "https://upload.wikimedia.org/wikipedia/en/1/16/Jirisan_%28TV_series%29.jpg",
    "The Legend of the Blue Sea": "https://upload.wikimedia.org/wikipedia/en/thumb/6/69/Legend_of_the_Blue_Sea_Poster.jpg/330px-Legend_of_the_Blue_Sea_Poster.jpg",
    "My Love from the Star": "https://upload.wikimedia.org/wikipedia/en/b/ba/You_Who_Came_From_the_Stars_Cover.jpg",
    "The Glory": "https://upload.wikimedia.org/wikipedia/en/7/79/The_Glory_TV_series.jpg",
    "Now, We Are Breaking Up": "https://upload.wikimedia.org/wikipedia/en/4/48/Now%2C_We_Are_Breaking_Up.jpg",
    "That Winter, the Wind Blows": "https://upload.wikimedia.org/wikipedia/en/b/b2/That_Winter%2C_The_Wind_Blows-poster.jpg",
    "Doctor Slump": "https://upload.wikimedia.org/wikipedia/en/8/8a/Doctor_Slump_%28TV_series%29_poster.jpg",
    "Sisyphus: The Myth": "https://upload.wikimedia.org/wikipedia/en/c/c5/Sisyphus_The_Myth.jpeg",
    "Pinocchio": "https://upload.wikimedia.org/wikipedia/en/a/af/PinocchioPromotionalPoster.jpg",
    "The Heirs": "https://upload.wikimedia.org/wikipedia/en/f/f7/The_Inheritors_poster.jpg",
    "Doona!": "https://upload.wikimedia.org/wikipedia/en/2/29/Doona%21.jpg",
    "Vagabond": "https://upload.wikimedia.org/wikipedia/en/5/51/Vagabond_2019.jpg",
    "Uncontrollably Fond": "https://upload.wikimedia.org/wikipedia/en/6/69/Uncontrollably_fond_poster.jpg",
    "Hotel Del Luna": "https://upload.wikimedia.org/wikipedia/en/0/00/Hotel_Del_Luna.jpg",
    "My Mister": "https://upload.wikimedia.org/wikipedia/en/thumb/3/31/MyMisterposter.jpg/330px-MyMisterposter.jpg",
    "Moon Lovers: Scarlet Heart Ryeo": "https://upload.wikimedia.org/wikipedia/en/0/0f/Scarletheartryeoposter.jpg",
    "The Producers": "https://upload.wikimedia.org/wikipedia/en/thumb/9/98/KBS_The_Producers_promo_poster.jpg/330px-KBS_The_Producers_promo_poster.jpg",
    "Dream High": "https://upload.wikimedia.org/wikipedia/en/thumb/d/d2/DreamHigh_PromotionalPoster.png/330px-DreamHigh_PromotionalPoster.png",
    "My Lovely Liar": "https://upload.wikimedia.org/wikipedia/en/8/88/My_Lovely_Liar.png",
    "Love Alarm": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Love_Alarm_title_card.png/330px-Love_Alarm_title_card.png",
    "Love Alarm 2": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Love_Alarm_title_card.png/330px-Love_Alarm_title_card.png",
    "River Where the Moon Rises": "https://upload.wikimedia.org/wikipedia/en/3/32/River_Where_the_Moon_Rises_%28%EB%8B%AC%EC%9D%B4_%EB%9C%A8%EB%8A%94_%EA%B0%95%29.jpg",
    "Link: Eat, Love, Kill": "https://upload.wikimedia.org/wikipedia/en/d/d6/Link%3B_Eat%2C_Love%2C_Kill.jpg",
    "Tempted": "https://upload.wikimedia.org/wikipedia/en/thumb/2/20/The_Great_Seducer_poster.jpg/330px-The_Great_Seducer_poster.jpg",
    "My Name": "https://upload.wikimedia.org/wikipedia/en/9/9c/My_Name_TV_series.jpg",
    "Nevertheless": "https://upload.wikimedia.org/wikipedia/en/5/56/Nevertheless_%28TV_series%29.jpg",
    "The World of the Married": "https://upload.wikimedia.org/wikipedia/en/7/76/The_World_of_the_Married.jpg",
    "Gyeongseong Creature": "https://upload.wikimedia.org/wikipedia/en/thumb/0/00/Gyeongseong_Creature_%28title_card%29.png/330px-Gyeongseong_Creature_%28title_card%29.png",
    "My Demon": "https://upload.wikimedia.org/wikipedia/en/0/05/My_Demon.jpg",
    "Clean with Passion for Now": "https://upload.wikimedia.org/wikipedia/en/3/33/Clean_with_Passion_for_Now-poster.jpg",
    "Love in the Moonlight": "https://upload.wikimedia.org/wikipedia/en/5/55/Love_in_the_Moonlight-official_poster.jpg",
    "Hometown Cha-Cha-Cha": "https://upload.wikimedia.org/wikipedia/en/3/3e/Hometown_Cha-Cha-Cha.jpg",
    "Our Blues": "https://upload.wikimedia.org/wikipedia/en/2/2f/Our_Blues_%28TV_series%29.jpeg",
    "Oh My Venus": "https://upload.wikimedia.org/wikipedia/en/8/89/Oh_My_Venus_%28%EC%98%A4_%EB%A7%88%EC%9D%B4_%EB%B9%84%EB%84%88%EC%8A%A4%29_Promotional_poster.jpg",
    "Crash Landing on You": "https://upload.wikimedia.org/wikipedia/en/5/5e/Crash_Landing_on_You_poster.png",
    "Something in the Rain": "https://upload.wikimedia.org/wikipedia/en/0/07/Something_in_the_Rain.jpg",
    "Twenty Five Twenty One": "https://upload.wikimedia.org/wikipedia/en/1/15/Twenty-Five_Twenty-One.jpg",
    "Vincenzo": "https://upload.wikimedia.org/wikipedia/en/5/5b/Vincenzo_TV_series.jpg",
    "Be Melodramatic": "https://upload.wikimedia.org/wikipedia/en/d/de/BeMelodramaticposter.jpg",
    "Sweet Home": "https://upload.wikimedia.org/wikipedia/en/thumb/f/f7/Sweet_Home_-_TV_series_%28title_card%29.png/330px-Sweet_Home_-_TV_series_%28title_card%29.png",
    "Sweet Home 3": "https://upload.wikimedia.org/wikipedia/en/thumb/f/f7/Sweet_Home_-_TV_series_%28title_card%29.png/330px-Sweet_Home_-_TV_series_%28title_card%29.png",
    "Youth of May": "https://upload.wikimedia.org/wikipedia/en/9/95/Youth_of_May_poster.jpg",
    "Strong Woman Do Bong-soon": "https://upload.wikimedia.org/wikipedia/en/thumb/2/28/StrongWomanDoBong-soon_%28Main_poster%29.jpg/250px-StrongWomanDoBong-soon_%28Main_poster%29.jpg",
    "Doom at Your Service": "https://upload.wikimedia.org/wikipedia/en/3/32/Doom_at_Your_Service.jpg",
    "Daily Dose of Sunshine": "https://upload.wikimedia.org/wikipedia/en/c/c3/Daily_Dose_of_Sunshine.jpg",
    "It's Okay to Not Be Okay": "https://upload.wikimedia.org/wikipedia/en/5/58/It%27s_Okay_to_Not_Be_Okay_Poster.jpg",
    "Lawless Lawyer": "https://upload.wikimedia.org/wikipedia/en/2/2f/Lawless_Lawyer-poster.jpg",
    "100 Days My Prince": "https://upload.wikimedia.org/wikipedia/en/f/f0/100_Days_My_Prince.jpg",
    "Suspicious Partner": "https://upload.wikimedia.org/wikipedia/en/e/e8/Suspicious_Partner_Main_Poster.jpg",
    "Shopping King Louie": "https://upload.wikimedia.org/wikipedia/en/c/ce/Shopping_King_Louie_Poster.jpg",
    "The Uncanny Counter": "https://upload.wikimedia.org/wikipedia/en/8/85/The_Uncanny_Counter_2.jpg",
    "School 2017": "https://upload.wikimedia.org/wikipedia/en/thumb/a/ae/KBS2-School_2017_%28poster%29.jpg/330px-KBS2-School_2017_%28poster%29.jpg",
    "What's Wrong with Secretary Kim": "https://upload.wikimedia.org/wikipedia/en/1/10/What%27s_Wrong_with_Secretary_Kim.jpg",
    "Healer": "https://upload.wikimedia.org/wikipedia/en/e/e3/Healer_TV_series-poster.jpg",
    "Forecasting Love and Weather": "https://upload.wikimedia.org/wikipedia/en/6/6c/Forecasting_Love_and_Weather_%282022_television_series%29_poster.jpg",
    "Mr. Queen": "https://upload.wikimedia.org/wikipedia/en/e/e7/Mr._Queen_poster.jpg",
    "Angel's Last Mission: Love": "https://upload.wikimedia.org/wikipedia/en/7/7e/Angel_s_Last_Mission%2C_Love.jpg",
    "Thirty But Seventeen": "https://upload.wikimedia.org/wikipedia/en/4/45/Still_17-poster.jpg",
    "My Golden Life": "https://upload.wikimedia.org/wikipedia/en/thumb/b/b2/My_Golden_Life_poster.jpg/330px-My_Golden_Life_poster.jpg",
    "See You in My 19th Life": "https://upload.wikimedia.org/wikipedia/en/5/57/See_You_in_My_19th_Life.png",
    "Goblin": "https://upload.wikimedia.org/wikipedia/en/thumb/6/68/Goblin_Poster.jpg/330px-Goblin_Poster.jpg",
    "The King: Eternal Monarch": "https://upload.wikimedia.org/wikipedia/en/thumb/d/dd/The_King_Eternal_Monarch.jpg/330px-The_King_Eternal_Monarch.jpg",
    "Cheese in the Trap": "https://upload.wikimedia.org/wikipedia/en/2/2c/Cheese_in_the_Trap_TV_poster.jpg",
    "Weightlifting Fairy Kim Bok-joo": "https://upload.wikimedia.org/wikipedia/en/b/bd/Weightlifting_Fairy_Kim_Bok_Joo_Poster.jpg",
    "Dr. Romantic 2": "https://upload.wikimedia.org/wikipedia/en/thumb/4/4a/Dr._Romantic_3_poster.jpg/330px-Dr._Romantic_3_poster.jpg",
    "Alchemy of Souls": "https://upload.wikimedia.org/wikipedia/en/b/b5/Alchemy_of_Souls.jpg",
    "Because This Is My First Life": "https://upload.wikimedia.org/wikipedia/en/e/ea/Because_This_is_My_First_Life.jpg",
    "Playful Kiss": "https://upload.wikimedia.org/wikipedia/en/f/f6/PlayfulKissPoster.jpg",
    "The Atypical Family": "https://upload.wikimedia.org/wikipedia/en/5/52/The_Atypical_Family_%28television_series%29_poster.png",
    "Delightfully Deceitful": "https://upload.wikimedia.org/wikipedia/en/8/80/Delightfully_Deceitful.jpg",
    "The Red Sleeve": "https://upload.wikimedia.org/wikipedia/en/a/a6/The_Red_Sleeve_Cuff.jpg",
    "Itaewon Class": "https://upload.wikimedia.org/wikipedia/en/9/99/Itaewon_Class.jpg",
    "Our Beloved Summer": "https://upload.wikimedia.org/wikipedia/en/2/29/Our_Beloved_Summer.jpg",
    "Kill Me, Heal Me": "https://upload.wikimedia.org/wikipedia/en/8/8a/KillMeHealMe-Poster.jpg",
    "Lucky Romance": "https://upload.wikimedia.org/wikipedia/en/1/12/Lucky_Romance_Poster.jpg",
    "Lovely Runner": "https://upload.wikimedia.org/wikipedia/en/6/67/Lovely_Runner.png",
    "Extraordinary You": "https://upload.wikimedia.org/wikipedia/en/4/43/Extraordinary_You.jpg",
    "SKY Castle": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7a/Sky_Castle.jpg/250px-Sky_Castle.jpg",
    "Mine": "https://upload.wikimedia.org/wikipedia/en/2/26/Mine_TV_series.jpg",
    "When the Camellia Blooms": "https://upload.wikimedia.org/wikipedia/en/d/d6/When_the_Camellia_Blooms.jpg",
    "Jealousy Incarnate": "https://upload.wikimedia.org/wikipedia/en/d/d6/Jealousy_Incarnate_Poster.jpg",
    "It's Okay, That's Love": "https://upload.wikimedia.org/wikipedia/en/f/f2/It%27s_Okay%2C_It%27s_Love-poster.jpg",
    "Pasta": "https://upload.wikimedia.org/wikipedia/en/b/bc/TV_Pasta_poster.jpg",
    "Empress Ki": "https://upload.wikimedia.org/wikipedia/commons/4/43/Empress_Gi.jpg",
    "Go Back Couple": "https://upload.wikimedia.org/wikipedia/en/thumb/b/b0/Confession_Couple_poster.png/330px-Confession_Couple_poster.png",
    "The Beauty Inside": "https://upload.wikimedia.org/wikipedia/en/6/69/The_Beauty_Inside_%28TV_series%29.jpg",
    "Another Miss Oh": "https://upload.wikimedia.org/wikipedia/en/0/09/Another_Oh_Hae-young.jpg",
    "Temperature of Love": "https://upload.wikimedia.org/wikipedia/en/3/3d/Temperature_of_Love.jpg",
    "You Are My Spring": "https://upload.wikimedia.org/wikipedia/en/0/09/You_Are_My_Spring.jpg",
    "Why Her": "https://upload.wikimedia.org/wikipedia/en/a/a1/Why_Her_poster.jpg",
    "Dr. Romantic 3": "https://upload.wikimedia.org/wikipedia/en/thumb/4/4a/Dr._Romantic_3_poster.jpg/330px-Dr._Romantic_3_poster.jpg",
}


def make_gallery(main_image):
    """Generate gallery variants from main image by using different sizes."""
    if not main_image:
        return []
    # Create different sized crops from the same Wikimedia image
    gallery = [main_image]
    # Add a larger version
    if "/330px-" in main_image:
        gallery.append(main_image.replace("/330px-", "/500px-"))
    elif "/250px-" in main_image:
        gallery.append(main_image.replace("/250px-", "/500px-"))
    else:
        gallery.append(main_image)
    return gallery


def update():
    docs = list(actresses_collection.find({}))
    for doc in docs:
        # Add poster URLs to dramas
        dramas = doc.get("dramas", [])
        for drama in dramas:
            drama["poster"] = POSTERS.get(drama["title"])

        # Add gallery from main image
        gallery = make_gallery(doc.get("image"))

        actresses_collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"dramas": dramas, "gallery": gallery}},
        )

    print(f"Updated {len(docs)} actresses with posters and galleries.")


if __name__ == "__main__":
    update()
