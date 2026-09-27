<?php
/**
 * Upcoming courses — used by the front page (next 2), the /courses/ list (all) and the RSS feed (all).
 *
 * A course is upcoming if its end date is today or later; courses without an end date count by
 * their start date. The end date is sometimes stored as an empty string, and courses imported
 * before 2030 have no end meta row at all.
 */

defined( 'ABSPATH' ) || exit;

function ct_upcoming( int $limit = 0 ): array {
	$today = current_time( 'Y-m-d' );

	$posts = get_posts(
		[
			'post_type'      => CT_POST_TYPE,
			'post_status'    => 'publish',
			'posts_per_page' => $limit > 0 ? $limit : -1,
			'meta_key'       => CT_START,
			'orderby'        => 'meta_value',
			'order'          => 'ASC',
			'meta_query'     => [
				'relation' => 'OR',
				[
					'key'     => CT_END,
					'value'   => $today,
					'compare' => '>=',
					'type'    => 'DATE',
				],
				[
					'relation' => 'AND',
					[
						'key'     => CT_END,
						'value'   => '',
						'compare' => '=',
					],
					[
						'key'     => CT_START,
						'value'   => $today,
						'compare' => '>=',
						'type'    => 'DATE',
					],
				],
				[
					'relation' => 'AND',
					[
						'key'     => CT_END,
						'compare' => 'NOT EXISTS',
					],
					[
						'key'     => CT_START,
						'value'   => $today,
						'compare' => '>=',
						'type'    => 'DATE',
					],
				],
			],
		]
	);

	$courses = [];
	foreach ( $posts as $post ) {
		$course = ct_shape( $post->ID );
		if ( null !== $course ) {
			$courses[] = $course;
		}
	}
	return $courses;
}

add_shortcode(
	'ct_next',
	static function (): string {
		$html = '';
		foreach ( ct_upcoming( 2 ) as $course ) {
			$html .= '<li><a href="' . esc_url( get_permalink( $course['id'] ) ) . '">' . esc_html( $course['title'] ) . '</a> ' . esc_html( ct_format_range( $course['start'], $course['end'] ) ) . '</li>';
		}
		return '' === $html ? '' : '<ul class="ct-next">' . $html . '</ul>';
	}
);

add_shortcode(
	'ct_list',
	static function (): string {
		$rows = '';
		foreach ( ct_upcoming() as $course ) {
			$rows .= '<tr><td>' . esc_html( ct_format_range( $course['start'], $course['end'] ) ) . '</td><td>' . esc_html( $course['title'] ) . '</td><td>' . esc_html( $course['city'] ) . '</td></tr>';
		}
		return '<table class="ct-list">' . $rows . '</table>';
	}
);
