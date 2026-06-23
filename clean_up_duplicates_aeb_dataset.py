from helper import *
import os
import pickle
import time

DESTINATION_DIR = "/Users/tarek/github/gogogo/staging"
PRO_DIR_ROOT = "/Users/tarek/github/gogogo/pro_games"

MAX_MOVES_IN_A_GAME = 400
SOURCE_DIR = "/Users/tarek/github/gogogo/bulk_datasets/AEB/Cho_Chikun"
PRO_DIR = ["/Users/tarek/github/gogogo/pro_games/Cho Chikun"]

### DUPES
# find_common_prefix(move_list_a, move_list_b) → index where games first diverge
# similarity_score(move_list_a, move_list_b) → float 0–1 based on common prefix length relative to total
# is_prefix_game(move_list_a, move_list_b) → one game is a truncated version of the other
# find_duplicate_candidates(fingerprint_db) → exact match lookup
# find_similar_candidates(fingerprint_db, threshold) → near-duplicate clustering
# classify_discrepancy(move_list_a, move_list_b) → single divergence vs scattered vs prefix

def get_similar_games_sgf_filepaths(root_dir: str = DESTINATION_DIR) -> list[str]:
    filepaths = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # filter subdirs in place so os.walk only descends into matching ones
        dirnames[:] = [d for d in dirnames if '- DUPLICATE' not in d]
        for filename in filenames:
            if filename.endswith('.sgf'):
                filepaths.append(os.path.join(dirpath, filename))
    return filepaths

def get_mapping_aeb_similar_pros_to_existing_pro_filepath():
    base_dataset = DESTINATION_DIR
    return {f'{base_dataset}/Takagawa Kaku - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Takagawa Kaku',
            f'{base_dataset}/Cho Chikun - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Cho Chikun',
            f'{base_dataset}/Honinbo Shusaku - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Honinbo Shusaku',
            f'{base_dataset}/Honinbo Shusai - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Honinbo Shusai',
            f'{base_dataset}/Honinbo Dosaku - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Honinbo Dosaku',
            f'{base_dataset}/Honinbo Jowa - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Honinbo Jowa',
            f'{base_dataset}/Go Seigen - SIMILAR BUT NOT DUPLICATE': f'{PRO_DIR_ROOT}/Go Seigen'
        }

def get_parent_dir(filepath: str) -> str:
    return "/".join(filepath.split("/")[:-1])

def load_similarity_scores() -> dict:
    try:
        with open('mapping_similar_game_fp_to_similarity_score.pk1', 'rb') as f:
            mapping_similar_game_fp_to_similarity_score = pickle.load(f)
        return mapping_similar_game_fp_to_similarity_score
    except Exception as e:
        return {}
    
def process_similarity_prediction(similar_game_filepath: str, prediction: list[tuple]):
    # to do: handle >1 prediction for a similar_game_filepath

    aeb_filepath = similar_game_filepath
    (recommended_pro_game_filepath, similarity_score) = prediction[0]

    return classify_discrepancy(aeb_filepath, recommended_pro_game_filepath)

def main():
    similar_games_to_process = get_similar_games_sgf_filepaths()
    print(f"\n{len(similar_games_to_process)} games to process. \n")

    # aeb dir of duplicates -> existing dir of relevant pro games
    mapping_aeb_similar_pros_to_existing_pro_filepath = get_mapping_aeb_similar_pros_to_existing_pro_filepath()

    # aeb filepath which is a duplicate -> existing dir of relevant pro games
    mapping_similar_game_fp_to_existing_pro_dir = {k: mapping_aeb_similar_pros_to_existing_pro_filepath[get_parent_dir(k)] for k in similar_games_to_process}

    # aeb filepath which is a duplicate -> (filepath of similar game, similarity score)
    mapping_similar_game_fp_to_similarity_score = load_similarity_scores()
    if mapping_similar_game_fp_to_similarity_score == {}:
        for sg in similar_games_to_process:
            existing_pro_dir = mapping_similar_game_fp_to_existing_pro_dir[sg]
            mapping_similar_game_fp_to_similarity_score[sg] = find_similar_candidates(sg, existing_pro_dir)

    counter = 1
    for game in sorted([k for k in mapping_similar_game_fp_to_similarity_score if 'Shusaku' in k]):
        print(f"game #{counter}")
        # breakpoint()
        print(f"A: {game}")
        if mapping_similar_game_fp_to_similarity_score[game] == []:
            print(">>> This game has no match, despite having a similar-looking game!\n")
            counter += 1
            # e.g.
            # game='/Users/tarek/github/gogogo/staging/Honinbo Shusaku - SIMILAR BUT NOT DUPLICATE/18570601-Yamamoto Samutsu-Honinbo Shusaku.sgf'
            # similar_looking_game='/Users/tarek/github/gogogo/pro_games/Honinbo Shusaku/18570601-Yamamoto Samutsu-Honinbo Shusaku.sgf'
            continue
        print(f"B: {mapping_similar_game_fp_to_similarity_score[game][0][0]}")
        print(f"Score: {mapping_similar_game_fp_to_similarity_score[game][0][1]}")
        similarity_prediction = mapping_similar_game_fp_to_similarity_score[game]
        if len(similarity_prediction) == 1:
            try:
                sp = process_similarity_prediction(game, similarity_prediction)
                print(process_similarity_prediction(game, similarity_prediction))
                print("\n")
                if sp == None:
                    breakpoint()
                # breakpoint()
            except Exception as e:
                # this has to do with passes being represented as None
                print("Error... skipping...")
                print(e)
        counter += 1

    # start with entries w/ more than 1 match:
    # [k for k in mapping_similar_game_fp_to_similarity_score if len(mapping_similar_game_fp_to_similarity_score[k]) > 1]

    # breakpoint()

if __name__ == '__main__':
    # # these 2 games are canonical equivalents
    # aeb_fp = "/Users/tarek/github/gogogo/staging/Honinbo Shusaku - SIMILAR BUT NOT DUPLICATE/18510504-Murase Yakichi-Honinbo Shusaku.sgf"
    # my_fp = "/Users/tarek/github/gogogo/pro_games/Honinbo Shusaku/18510504-Murase Yakichi-Honinbo Shusaku.sgf"

    # # these 2 games have the same datestamp but are actually different games
    # aeb = "/Users/tarek/github/gogogo/staging/Honinbo Shusaku - SIMILAR BUT NOT DUPLICATE/18570601-Yamamoto Samutsu-Honinbo Shusaku.sgf"
    # fp = "/Users/tarek/github/gogogo/pro_games/Honinbo Shusaku/18570601-Yamamoto Samutsu-Honinbo Shusaku.sgf"

    # # these 2 games are the same but the players are switched - who is who?!
    # aa = "/Users/tarek/github/gogogo/staging/Honinbo Shusaku - SIMILAR BUT NOT DUPLICATE/18521104-Ota Yuzo-Honinbo Shusaku.sgf"
    # bb = "/Users/tarek/github/gogogo/pro_games/Honinbo Shusaku/18521104-Honinbo Shusaku-Ota Yuzo.sgf"
    
    # # these 2 games are the same but aren't classified as such
    # aaa = '/Users/tarek/github/gogogo/staging/Honinbo Shusaku - SIMILAR BUT NOT DUPLICATE/18490131-Honinbo Shusaku-Ito Showa.sgf'
    # bbb = '/Users/tarek/github/gogogo/pro_games/Honinbo Shusaku/18490131-Honinbo Shusaku-Ito Showa.sgf'
    main()