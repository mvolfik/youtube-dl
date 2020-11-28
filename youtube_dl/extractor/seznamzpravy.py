# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime

from youtube_dl.utils import try_get, urljoin
from .common import InfoExtractor


class SDNIE(InfoExtractor):
    _VALID_URL = r"https?://.*.sdn\.cz/~SEC1~expire-[0-9]+~scope-video~[a-zA-Z0-9-]+/v_[0-9]+/vmd/(?:.*?_)?(?P<id>[0-9a-f]+)\?fl=.*"

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(url, video_id)
        return {
            "id": video_id,
            "title": "Unknown",
            "url": urljoin(url, json_data["data"]["mp4"]["480p"]["url"]),
        }


class SeznamZpravyIE(InfoExtractor):
    _VALID_URL = r"https?://(?:www\.)?seznamzpravy\.cz/clanek/(?:.*-)?(?P<id>[0-9]+)"

    _TESTS = [
        {
            # two videos on one page, with SDN URL
            "url": "https://www.seznamzpravy.cz/clanek/jejich-svet-na-nas-utoci-je-lepsi-branit-se-na-jejich-pisecku-rika-reziser-a-major-v-zaloze-marhoul-35990",
            "info_dict": {
                "id": "35990",
                "title": "md5:6011c877a36905f28f271fcd8dcdb0f2",
                "description": "md5:933f7b06fa337a814ba199d3596d27ba",
            },
            "playlist_count": 2,
        },
        {
            # video with live stream URL
            "url": "https://www.seznam.cz/zpravy/clanek/znovu-do-vlady-s-ano-pavel-belobradek-ve-volebnim-specialu-seznamu-38489",
            "info_dict": {
                "id": "38489",
                "title": "md5:8fa1afdc36fd378cf0eba2b74c5aca60",
                "description": "md5:428e7926a1a81986ec7eb23078004fb4",
            },
            "playlist_count": 1,
        },
        # tests above are copied from previous version of this extractor
        {
            # test
            "url": "https://www.seznamzpravy.cz/clanek/64087"
        },
    ]

    # some magic value for now, not sure where it comes from, would probably require reversing the javascript to some extent
    _MAGIC = "spl2,3,VOD"

    def _process_item(self, item, video_id):
        if item["itemType"] == "live":
            live = True
            url = self._download_json(item["liveStreamUrl"] + self._MAGIC, video_id)[
                "Location"
            ]
            duration = None
            poster = None
        elif item["itemType"] == "video":
            live = False
            url = item["video"]["sdn"] + self._MAGIC
            duration = try_get(
                item, lambda x: x["video"]["videoInfo"]["duration"], expected_type=int
            )
            if duration is not None:
                duration /= 1000
            poster = try_get(
                item, lambda x: x["video"]["poster"]["url"], expected_type=str
            )
        else:
            return

        title = item["title"]
        author = item.get("author")
        keywords = item.get("keywords")
        upload_date = item.get("_created")
        try:
            upload_date = datetime.strptime(upload_date, "%Y-%m-%d %H:%M:%S").date()
        except KeyboardInterrupt:
            pass
        return {
            "_type": "url",
            "ie_key": SDNIE.ie_key(),
            "url": url,
            "title": title,
            "creator": author,
            "duration": duration,
            "tags": keywords,
            "thumbnail": poster,
            "is_live": live,
            "upload_date": upload_date,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(
            "https://api.seznamzpravy.cz/v1/documents/" + video_id, video_id
        )
        videos = []
        captiondata = self._process_item(json_data["caption"], video_id=video_id)
        if captiondata is not None:
            captiondata["title"] = json_data["title"]
            videos.append(captiondata)
        for item in json_data["content"]:
            if item["component"] == "molecule.figure.Figure":
                result = self._process_item(
                    item["properties"]["media"], video_id=video_id
                )
                if result:
                    videos.append(result)
        return {"_type": "playlist", "entries": videos}
