import time
from PIL import Image, ImageStat
import click


def rotate_2d_array(arr, degrees):
    if degrees == 0:
        new_array = arr
    elif degrees == 90:
        new_array = list(zip(*arr[::-1]))
    elif degrees == 180:
        new_array = [row[::-1] for row in arr[::-1]]
    elif degrees == 270:
        new_array = list(zip(*arr))[::-1]
    else:
        raise ValueError("Invalid degrees. Degrees should be 90, 180, or 270.")
    return new_array


def parse_single_grid2array(img: Image.Image, num_columns, rotation=180):
    pixel_size = img.width // num_columns
    num_lines = img.height // pixel_size
    blocks = [[] for _ in range(num_columns)]
    for x in range(num_columns):
        for y in range(num_lines):
            target = img.crop((x * pixel_size, y * pixel_size, (x + 1) * pixel_size, (y + 1) * pixel_size))
            stat = ImageStat.Stat(target)
            grayscale = sum(stat.median) / 3
            if grayscale < 125:
                blocks[x].append(1)
                continue
            if grayscale >= 125:
                blocks[x].append(0)
                continue
    rotated_blocks = rotate_2d_array(blocks, degrees=rotation)
    rotated_str_array = [
        "".join([str(char) for char in line])
        for line in rotated_blocks
    ]
    rotated_verbose_str = ""

    for line in rotated_str_array:
        line = line.replace("0", "░░")
        line = line.replace("1", "██")
        rotated_verbose_str += "%s\n" % line

    output_c_array = []
    for line in rotated_str_array:
        output_c_array.append(
            int(line, base=2),
        )
    return output_c_array, rotated_verbose_str


def get_grids(img: Image.Image, num_horizontal_grids, num_vertical_grids):
    grid_width = img.width // num_horizontal_grids
    grid_height = img.height // num_vertical_grids
    grids = []
    for num_vertical_grid_index in range(num_vertical_grids):
        grids.append([])
        for num_horizontal_grid_index in range(num_horizontal_grids):
            crop_rectangle = (
                    num_horizontal_grid_index * grid_width,
                    num_vertical_grid_index * grid_height,
                    (num_horizontal_grid_index + 1) * grid_width,
                    (num_vertical_grid_index + 1) * grid_height,
            )
            new_img = img.crop(crop_rectangle)
            grids[num_vertical_grid_index].append(new_img)
    return grids


def format_single_art_output(bitmap_hor_index, bitmap_vec_index, output_array, verbose_mode, variable_name="custom_bitmap"):
    comment_tpl = """
/**
 * bitmap {:0>4}/{:0>4}
{}
 */\n"""
    content = ""
    final_var_name = f"{variable_name}_{bitmap_hor_index:0<4}_{bitmap_vec_index:0<4}"
    bitmap_tpl = "const char %s[] = {%s};"
    c_array, ascii_art = output_array
    if verbose_mode:
        content += comment_tpl.format(bitmap_hor_index, bitmap_vec_index, ascii_art)
    single_bitmap = bitmap_tpl % (final_var_name, ",".join([str(the_byte) for the_byte in c_array]))
    content += single_bitmap
    return final_var_name, content


def format_output(grids, num_hor_pieces_per_block, rotation, verbose, variable_name):
    output = """// Header file generated by img2pixels for LED display\n"""
    num_total_grids = 0
    final_var_names = []
    for vec_index, line_array in enumerate(grids):
        for hor_index, grid in enumerate(line_array):
            out_pixels = parse_single_grid2array(
                grid,
                num_hor_pieces_per_block,
                rotation=rotation,
            )
            final_var_name, content = format_single_art_output(vec_index, hor_index, out_pixels, verbose, variable_name)
            output += content
            num_total_grids += 1
            final_var_names.append(final_var_name)
    output += """\n
const char %s_width[] = {%s};
const char* %s_addr[] = {%s};
    """ % (
        variable_name,
        ", ".join([str(num_hor_pieces_per_block)] * num_total_grids),
        variable_name,
        ", ".join(["&%s" % name for name in final_var_names])
    )
    return output


def parse_image2array(
        input_file,
        out_file,
        num_horizontal_grids=1, num_vertical_grids=1,
        num_hor_pieces_per_block=1,
        rotation=180,
        verbose=True,
        variable_name="custom_bitmap",
):
    img = Image.open(input_file)
    grids = get_grids(img, num_horizontal_grids, num_vertical_grids)
    output = format_output(grids, num_hor_pieces_per_block, rotation, verbose, variable_name)
    out_file.write(
        output
    )
    return output


@click.group("defaults")
def entry():
    pass


@click.argument("input_file")
@click.option("-o", "--out-file", default=None, type=click.File(mode="w", encoding="utf-8"))
@click.option("-nhg", "--num_horizontal_grids", default=1, type=click.INT)
@click.option("-nvg", "--num_vertical_grids", default=1, type=click.INT)
@click.option("-nhppb", "--num_hor_pieces_per_block", default=1, type=click.INT)
@click.option("-r", "--rotation", default="180", type=click.Choice(("0", "90", "180", "270")))
@click.option("-name", "--variable_name", default="custom_bitmap", type=click.STRING)
@click.option("-v", "--verbose", default=False, type=click.BOOL, is_flag=True, show_default=True)
@entry.command("cli")
def cli(input_file,
        out_file,
        num_horizontal_grids,
        num_vertical_grids,
        num_hor_pieces_per_block,
        rotation,
        verbose,
        variable_name,
        ):
    if out_file is None:
        out_file = open("custom_bitmap.h", "w", encoding="utf-8")
    output = parse_image2array(
        input_file,
        out_file,
        num_horizontal_grids, num_vertical_grids,
        num_hor_pieces_per_block,
        int(rotation),
        verbose,
        variable_name,
    )
    out_file.close()
    print(output)


def http_server():
    pass


if __name__ == '__main__':
    entry()
